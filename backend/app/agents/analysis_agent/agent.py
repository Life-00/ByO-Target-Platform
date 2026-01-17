"""
Analysis Agent Implementation

RAG-based document analysis agent that:
1. Retrieves relevant chunks from ChromaDB based on selected documents
2. Enriches with page numbers from PostgreSQL
3. Generates evidence-based answers with citations
4. Provides exact sources (document title, page number, text excerpt)
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.analysis_agent.schemas import (
    AnalysisAgentRequest,
    AnalysisAgentResponse,
    CitationInfo
)
from app.agents.analysis_agent.prompt import (
    SYSTEM_PROMPT,
    ANALYSIS_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS
)
from app.services.llm_service import get_llm_service
from app.services.embedding_service import get_embedding_service
from app.db.models import Document, DocumentChunk
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.config import settings

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """
    Analysis Agent
    RAG-based document analysis with precise citations
    """

    def __init__(self, db: AsyncSession = None):
        """Initialize analysis agent"""
        super().__init__()
        self.agent_type = "analysis_agent"
        self.system_prompt = SYSTEM_PROMPT
        self.llm_service = get_llm_service()
        self.embedding_service = get_embedding_service()
        self.db = db
        self.collection = None
        
    def _get_chroma_collection(self):
        """Lazy load ChromaDB connection"""
        if self.collection is None:
            try:
                import chromadb
                self.chroma_client = chromadb.HttpClient(
                    host=settings.chromadb_host,
                    port=settings.chromadb_port
                )
                self.collection = self.chroma_client.get_or_create_collection(
                    name="document_embeddings"
                )
                logger.info("[AnalysisAgent] ChromaDB connected")
            except Exception as e:
                logger.error(f"[AnalysisAgent] ChromaDB connection failed: {str(e)}")
                self.collection = None
        return self.collection

    async def execute(self, request: AnalysisAgentRequest) -> AnalysisAgentResponse:
        """
        Execute analysis workflow
        
        Args:
            request: AnalysisAgentRequest with question and selected documents
            
        Returns:
            AnalysisAgentResponse with answer and citations
        """
        try:
            logger.info(f"[AnalysisAgent] Analyzing: {request.content[:50]}...")
            logger.info(f"[AnalysisAgent] Selected documents: {len(request.selected_documents)}")

            if not request.selected_documents:
                return AnalysisAgentResponse(
                    success=False,
                    answer="",
                    error="No documents selected for analysis"
                )

            # Step 1: Get document IDs
            document_ids = [doc.get('id') for doc in request.selected_documents if doc.get('id')]
            if not document_ids:
                return AnalysisAgentResponse(
                    success=False,
                    answer="",
                    error="No valid document IDs found"
                )

            logger.info(f"[AnalysisAgent] Analyzing document IDs: {document_ids}")

            # Step 2: Retrieve relevant chunks from ChromaDB
            relevant_chunks = await self._retrieve_relevant_chunks(
                query=request.content,
                document_ids=document_ids,
                top_k=request.top_k
            )
            
            if not relevant_chunks:
                return AnalysisAgentResponse(
                    success=True,
                    answer="선택된 문서에서 관련 내용을 찾을 수 없습니다. 다른 문서를 선택하거나 질문을 더 구체적으로 작성해주세요.",
                    citations=[],
                    documents_analyzed=len(document_ids),
                    chunks_retrieved=0
                )

            logger.info(f"[AnalysisAgent] Retrieved {len(relevant_chunks)} relevant chunks")

            # Step 3: Enrich chunks with document metadata
            enriched_chunks = await self._enrich_chunks_with_metadata(relevant_chunks)

            # Step 4: Generate answer using LLM
            answer, tokens_used = await self._generate_answer(
                question=request.content,
                analysis_goal=request.analysis_goal,
                chunks=enriched_chunks
            )

            # Step 5: Extract citations
            citations = self._extract_citations(enriched_chunks)

            return AnalysisAgentResponse(
                success=True,
                answer=answer,
                citations=citations,
                documents_analyzed=len(document_ids),
                chunks_retrieved=len(relevant_chunks),
                tokens_used=tokens_used,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "analysis_goal": request.analysis_goal
                }
            )

        except Exception as e:
            logger.error(f"[AnalysisAgent] Error: {str(e)}")
            return AnalysisAgentResponse(
                success=False,
                answer="",
                error=str(e)
            )

    async def _retrieve_relevant_chunks(
        self,
        query: str,
        document_ids: List[int],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from ChromaDB for selected documents
        """
        try:
            collection = self._get_chroma_collection()
            if not collection:
                raise Exception("ChromaDB collection not available")

            # Generate query embedding
            embed_result = await self.embedding_service.embed(query, use_cache=True)
            query_embedding = embed_result["embedding"]

            # Query ChromaDB with document_id filter
            # Get more results since we'll filter by document_ids
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * len(document_ids),  # Get enough for all documents
                include=["documents", "metadatas", "distances"]
            )

            # Filter and sort by document_ids
            relevant_chunks = []
            for i, metadata in enumerate(results["metadatas"][0]):
                doc_id = metadata.get("document_id")
                if doc_id in document_ids:
                    chunk_data = {
                        "chroma_id": results["ids"][0][i],
                        "document_id": doc_id,
                        "chunk_index": metadata.get("chunk_index"),
                        "page_number": metadata.get("page_number"),
                        "text": results["documents"][0][i],
                        "distance": results["distances"][0][i],
                        "relevance_score": 1.0 / (1.0 + results["distances"][0][i])  # Convert distance to score
                    }
                    relevant_chunks.append(chunk_data)

            # Sort by relevance and limit to top_k
            relevant_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
            return relevant_chunks[:top_k]

        except Exception as e:
            logger.error(f"[AnalysisAgent] Chunk retrieval failed: {str(e)}")
            return []

    async def _enrich_chunks_with_metadata(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich chunks with document metadata from PostgreSQL
        """
        try:
            # Get unique document IDs
            doc_ids = list(set(chunk["document_id"] for chunk in chunks))

            # Fetch document metadata
            result = await self.db.execute(
                select(Document).where(Document.id.in_(doc_ids))
            )
            documents = {doc.id: doc for doc in result.scalars().all()}

            # Enrich each chunk
            enriched = []
            for chunk in chunks:
                doc_id = chunk["document_id"]
                if doc_id in documents:
                    doc = documents[doc_id]
                    enriched.append({
                        **chunk,
                        "document_title": doc.title,
                        "document_filename": doc.file_name
                    })
                else:
                    enriched.append(chunk)

            return enriched

        except Exception as e:
            logger.error(f"[AnalysisAgent] Metadata enrichment failed: {str(e)}")
            return chunks

    async def _generate_answer(
        self,
        question: str,
        analysis_goal: Optional[str],
        chunks: List[Dict[str, Any]]
    ) -> tuple[str, int]:
        """
        Generate answer using LLM with retrieved chunks as context
        """
        try:
            # Format context chunks
            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                doc_title = chunk.get("document_title", "Unknown Document")
                page_num = chunk.get("page_number", "?")
                text = chunk.get("text", "")
                
                context_parts.append(
                    f"[{i}] 문서: {doc_title}, 페이지: {page_num}\n{text}\n"
                )

            context_text = "\n---\n".join(context_parts)

            # Build prompt
            user_prompt = ANALYSIS_PROMPT.format(
                analysis_goal=analysis_goal or "일반 분석",
                question=question,
                context_chunks=context_text
            )

            # Call LLM
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=self.system_prompt,
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS
            )

            answer = response["content"]
            tokens_used = response["usage"]["total_tokens"]

            return answer, tokens_used

        except Exception as e:
            logger.error(f"[AnalysisAgent] Answer generation failed: {str(e)}")
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}", 0

    def _extract_citations(self, chunks: List[Dict[str, Any]]) -> List[CitationInfo]:
        """
        Extract citation information from chunks
        """
        citations = []
        for chunk in chunks:
            try:
                citation = CitationInfo(
                    document_id=chunk["document_id"],
                    document_title=chunk.get("document_title", "Unknown"),
                    page_number=chunk.get("page_number", 0),
                    chunk_index=chunk.get("chunk_index", 0),
                    text_excerpt=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                    relevance_score=chunk.get("relevance_score", 0.0)
                )
                citations.append(citation)
            except Exception as e:
                logger.warning(f"[AnalysisAgent] Failed to create citation: {str(e)}")
                continue

        return citations
