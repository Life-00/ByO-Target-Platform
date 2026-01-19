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
from sqlalchemy import select

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

# ReAct Reasoning Tool용
from app.tools.reasoning.react_quality_gate import (
    react_quality_gate,
    EvidenceItem,
)

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

            # Step 1: Get document IDs (allow empty for "search all documents" mode)
            document_ids = []
            if request.selected_documents:
                document_ids = [doc.get('id') for doc in request.selected_documents if doc.get('id')]
            
            if request.selected_documents and not document_ids:
                return AnalysisAgentResponse(
                    success=False,
                    answer="",
                    error="No valid document IDs found"
                )

            if not document_ids and request.selected_documents:
                logger.warning("[AnalysisAgent] Specific documents selected but no valid IDs found")
            elif not document_ids:
                logger.info("[AnalysisAgent] No documents specified - searching across all available documents")

            logger.info(f"[AnalysisAgent] Analyzing document IDs: {document_ids if document_ids else 'ALL'}")

            # Step 2: Retrieve relevant chunks from ChromaDB + ReAct loop
            MAX_REACT_ATTEMPTS = 5  # 무한 루프 방지
            current_query = request.content
            current_top_k = request.top_k
            relevant_chunks: List[Dict[str, Any]] = []
            last_gate_result = None
            no_chunks_attempts = 0

            for attempt in range(MAX_REACT_ATTEMPTS):
                logger.info(f"[AnalysisAgent][ReAct] Attempt {attempt + 1}")

                relevant_chunks = await self._retrieve_relevant_chunks(
                    query=current_query,
                    document_ids=document_ids,
                    top_k=current_top_k,
                    min_score=request.min_relevance_score
                )

                if not relevant_chunks:
                    no_chunks_attempts += 1
                    logger.info(f"[AnalysisAgent][ReAct] No chunks retrieved (attempt {no_chunks_attempts})")
                    
                    # Aggressively increase search scope if no results
                    if no_chunks_attempts == 1:
                        current_top_k = max(50, current_top_k * 3)
                        logger.info(f"[AnalysisAgent][ReAct] Aggressive increase: top_k → {current_top_k}")
                        continue
                    elif no_chunks_attempts == 2:
                        current_query = await self._rewrite_query_with_llm(
                            request.content,
                            ["검색 결과 없음 - 쿼리 재작성 필요"],
                        )
                        logger.info(f"[AnalysisAgent][ReAct] Rewriting query due to no results: {current_query}")
                        continue
                    else:
                        # Give up and break after 2+ attempts
                        break

                evidence_items = [
                    EvidenceItem(
                        content=chunk["text"],
                        metadata={
                            "document_id": chunk.get("document_id"),
                            "document_title": chunk.get("document_title"),
                            "filename": chunk.get("filename", chunk.get("document_title", "Unknown")),
                            "section_type": chunk.get("section_type"),
                        }
                    )
                    for chunk in relevant_chunks
                ]

                gate_result = await react_quality_gate(
                    task_goal=request.analysis_goal or "RAG-based document analysis",
                    query=request.content,
                    evidence_items=evidence_items,
                    llm_service=self.llm_service,
                )

                last_gate_result = gate_result

                if gate_result.accept:
                    logger.info("[AnalysisAgent][ReAct] Gate accepted")
                    break

                logger.info(
                    f"[AnalysisAgent][ReAct] Gate rejected: "
                    f"{gate_result.failure_reasons}, next={gate_result.next_action}"
                )

                # 🔹 Act 단계 (상태 변화 필수)
                if gate_result.next_action == "increase_top_k":
                    old_top_k = current_top_k
                    current_top_k = current_top_k * 2  # Double the top_k for more results
                    logger.info(f"[AnalysisAgent][ReAct] Increasing top_k from {old_top_k} to {current_top_k}")

                elif gate_result.next_action == "rewrite_query":
                    current_query = await self._rewrite_query_with_llm(
                        request.content,
                        gate_result.failure_reasons,
                    )
                    logger.info(f"[AnalysisAgent][ReAct] Query rewritten to: {current_query}")

                elif gate_result.next_action == "ask_user_clarification":
                    # Try increasing top_k as an alternative to asking user
                    old_top_k = current_top_k
                    current_top_k = current_top_k * 2
                    logger.info(f"[AnalysisAgent][ReAct] User clarification requested, increasing top_k from {old_top_k} to {current_top_k}")

                elif gate_result.next_action == "stop":
                    break

                else:
                    break

            # 🔒 ReAct 최종 실패 → 답변 생성 차단
            if not relevant_chunks or not last_gate_result or not last_gate_result.accept:
                return AnalysisAgentResponse(
                    success=True,
                    answer=(
                        "선택된 문서만으로는 현재 질문에 답하기에 "
                        "근거가 충분하지 않습니다.\n\n"
                        f"사유: {', '.join(last_gate_result.failure_reasons) if last_gate_result else '근거 부족'}"
                    ),
                    citations=[],
                    documents_analyzed=len(document_ids),
                    chunks_retrieved=len(relevant_chunks),
                    metadata={
                        "react_attempts": attempt + 1,
                        "react_confidence": last_gate_result.confidence if last_gate_result else None,
                        "react_rationale": last_gate_result.rationale if last_gate_result else None,
                    }
                )


            # Step 3: Enrich chunks with document metadata
            enriched_chunks = await self._enrich_chunks_with_metadata(relevant_chunks)


            # Step 4: Generate answer using LLM (gate 통과 시만)
            answer, tokens_used = await self._generate_answer(
                question=request.content,
                analysis_goal=request.analysis_goal,
                chunks=enriched_chunks
            )


            # Step 5: Extract citations (use indices from answer or top chunks)
            citations = self._extract_citations(
                enriched_chunks,
                getattr(self, '_last_used_indices', set(range(min(len(enriched_chunks), 3))))
            )

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
        top_k: int,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from ChromaDB for selected documents
        Uses semantic search via embeddings for meaningful retrieval
        Falls back to PostgreSQL if ChromaDB is unavailable
        """
        try:
            collection = self._get_chroma_collection()
            if not collection:
                logger.warning("[AnalysisAgent] ChromaDB not available, using PostgreSQL fallback")
                return await self._retrieve_from_postgresql(query, document_ids, top_k)

            # Generate query embedding for semantic search
            logger.info(f"[AnalysisAgent] Searching for: {query}")
            embed_result = await self.embedding_service.embed(query, use_cache=True)
            query_embedding = embed_result["embedding"]
            logger.info(f"[AnalysisAgent] Query embedding generated (dim={len(query_embedding)})")

            # Normalize document_ids: convert all to integers for comparison
            document_ids_int = set(int(doc_id) if isinstance(doc_id, str) else doc_id for doc_id in document_ids)
            logger.info(f"[AnalysisAgent] Looking for documents: {document_ids_int}")

            # Query ChromaDB with where filter for selected documents
            # ChromaDB returns results sorted by distance (semantic similarity)
            where_filter = None
            if document_ids_int:
                # Build where filter to only search in selected documents
                where_filter = {
                    "document_id": {"$in": list(document_ids_int)}
                }
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(100, top_k * max(5, len(document_ids))),  # Get enough results
                where=where_filter,
                include=["documents", "metadatas", "distances", "embeddings"]
            )

            logger.info(f"[AnalysisAgent] ChromaDB returned {len(results['ids'][0])} results")
            # Process results and convert to chunk data
            relevant_chunks = []
            
            for i, chroma_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                doc_id_raw = metadata.get("document_id")
                # Normalize to integer for comparison
                doc_id = int(doc_id_raw) if isinstance(doc_id_raw, str) else doc_id_raw
                
                distance = results["distances"][0][i]
                relevance_score = 1.0 / (1.0 + distance)  # Convert L2 distance to similarity score
                
                # Very relaxed minimum score threshold - allow more results through
                # We'll filter quality in the ReAct gate
                if relevance_score < 0.3:  # Only filter truly low-relevance results
                    continue
                
                chunk_data = {
                    "chroma_id": chroma_id,
                    "document_id": doc_id,
                    "chunk_index": metadata.get("chunk_index"),
                    "filename": metadata.get("filename", metadata.get("document_title", "Unknown")),
                    "section_title": metadata.get("section_title", "Full Document"),
                    "text": results["documents"][0][i],
                    "distance": distance,
                    "relevance_score": relevance_score
                }
                relevant_chunks.append(chunk_data)

            # Sort by relevance score (descending) and limit to top_k
            relevant_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
            selected_chunks = relevant_chunks[:top_k]
            
            logger.info(f"[AnalysisAgent] Retrieved {len(selected_chunks)} relevant chunks via ChromaDB semantic search")
            if selected_chunks:
                logger.info(f"[AnalysisAgent] Top result scores: {[f'{c['relevance_score']:.3f}' for c in selected_chunks[:3]]}")
            
            return selected_chunks

        except Exception as e:
            logger.error(f"[AnalysisAgent] ChromaDB query error: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            logger.warning("[AnalysisAgent] Falling back to PostgreSQL keyword matching")
            return await self._retrieve_from_postgresql(query, document_ids, top_k)

    async def _rewrite_query_with_llm(
        self,
        original_query: str,
        failure_reasons: List[str],
    ) -> str:
        """
        Rewrite user query to improve semantic search retrieval
        Uses LLM to generate more specific search query based on failure reasons
        """
        try:
            prompt = f"""당신은 정보 검색 전문가입니다.

원래 질문: {original_query}
검색 실패 사유: {', '.join(failure_reasons) if failure_reasons else '관련 자료 없음'}

위의 실패 사유를 고려하여 원래 질문을 더 구체적이고
검색 엔진이 이해하기 쉽도록 한 문장으로 다시 작성하세요.
다시 작성한 질문만 출력하세요."""
            
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=128,
            )
            rewritten = response.get("content", original_query).strip()
            return rewritten if rewritten else original_query
            
        except Exception as e:
            logger.warning(f"[AnalysisAgent] Query rewriting failed: {str(e)}, using original")
            return original_query

    async def _retrieve_from_postgresql(
        self,
        query: str,
        document_ids: List[int],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Fallback: Retrieve chunks directly from PostgreSQL when ChromaDB is unavailable
        Uses improved keyword matching with fuzzy matching for better recall
        """
        try:
            if not self.db:
                logger.error("[AnalysisAgent] No database session available for fallback")
                return []

            # Convert document_ids to integers (in case they're strings)
            doc_ids_int = [int(doc_id) for doc_id in document_ids]

            # Get chunks with document metadata for filename
            from sqlalchemy.orm import joinedload
            result = await self.db.execute(
                select(DocumentChunk)
                .options(joinedload(DocumentChunk.document))
                .where(DocumentChunk.document_id.in_(doc_ids_int))
                .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
                .limit(top_k * 3)  # Get more than needed
            )
            chunks = result.scalars().all()

            if not chunks:
                logger.warning(f"[AnalysisAgent] No chunks found in PostgreSQL for documents: {document_ids}")
                return []

            # Improved keyword matching with substring and jamo matching
            query_lower = query.lower()
            query_words = query_lower.split()
            relevant_chunks = []
            
            for chunk in chunks:
                text_lower = (chunk.text_content or "").lower()
                score = 0.0
                
                # 1. Exact phrase match (highest priority)
                if query_lower in text_lower:
                    score += 10.0
                
                # 2. Substring matches (handles spacing variations like "연구방법" vs "연구 방법")
                for word in query_words:
                    if len(word) > 1:
                        # Check if word appears as substring
                        if word in text_lower:
                            score += 3.0
                        # Check if word appears with spaces removed
                        text_no_space = text_lower.replace(" ", "")
                        if word in text_no_space:
                            score += 2.0
                
                # 3. Individual character matches
                for char in query_lower:
                    if char not in [' ', ',', '.', '(', ')', '!', '?']:
                        if char in text_lower:
                            score += 0.1
                
                if score > 0:
                    chunk_data = {
                        "chroma_id": chunk.chroma_id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "filename": chunk.document.file_name if chunk.document else "Unknown",
                        "document_title": chunk.document.title if chunk.document else "Unknown",
                        "text": chunk.text_content,
                        "distance": 1.0 / (score + 1),  # Lower distance for higher score
                        "relevance_score": score
                    }
                    relevant_chunks.append(chunk_data)

            # Sort by relevance score and return top_k
            relevant_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
            logger.info(f"[AnalysisAgent] Retrieved {len(relevant_chunks[:top_k])} chunks from PostgreSQL fallback (scores: {[f'{c['relevance_score']:.1f}' for c in relevant_chunks[:3]]})")
            return relevant_chunks[:top_k]

        except Exception as e:
            logger.error(f"[AnalysisAgent] PostgreSQL fallback failed: {str(e)}")
            # Rollback transaction on error
            if self.db:
                await self.db.rollback()
            return []

    def _get_document_id(self, chunk: Dict[str, Any]) -> Optional[int]:
        return (
                chunk.get("document_id")
                or chunk.get("metadata", {}).get("document_id")
        )


    async def _enrich_chunks_with_metadata(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich chunks with document metadata from PostgreSQL
        """
        try:
            # Get unique document IDs
            doc_ids = list(
                set(
                    self._get_document_id(chunk)
                    for chunk in chunks
                    if self._get_document_id(chunk) is not None
                )
            )

            if not doc_ids:
                return chunks

            # Fetch document metadata
            result = await self.db.execute(
                select(Document).where(Document.id.in_(doc_ids))
            )
            documents = {doc.id: doc for doc in result.scalars().all()}

            # Enrich each chunk
            enriched = []
            for chunk in chunks:
                doc_id = self._get_document_id(chunk)
                base = {
                    **chunk,
                    "document_id": doc_id,   # 🔥 여기서 top-level로 승격
                }

                if doc_id in documents:
                    doc = documents[doc_id]
                    base.update({
                        "document_title": doc.title,
                        "document_filename": doc.file_name,
                    })
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
                filename = chunk.get("filename", chunk.get("document_title", "Unknown"))
                text = chunk.get("text", "")
                
                context_parts.append(
                    f"[{i}] 파일: {filename}\n{text}\n"
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
            
            # Extract citation indices from answer (e.g., [1], [2], [3])
            import re
            used_indices = set()
            for match in re.finditer(r'\[(\d+)\]', answer):
                idx = int(match.group(1)) - 1  # Convert to 0-based index
                if 0 <= idx < len(chunks):
                    used_indices.add(idx)
            
            # Store indices for citation extraction
            self._last_used_indices = used_indices if used_indices else set(range(min(len(chunks), 3)))

            return answer, tokens_used

        except Exception as e:
            logger.error(f"[AnalysisAgent] Answer generation failed: {str(e)}")
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}", 0

    def _extract_citations(self, chunks: List[Dict[str, Any]], used_indices: set = None) -> List[CitationInfo]:
        """
        Extract citation information from chunks
        Only include citations for chunks referenced in used_indices
        """
        if used_indices is None:
            used_indices = set(range(len(chunks)))
        
        citations = []
        for idx, chunk in enumerate(chunks):
            # Skip if this chunk index was not used in the answer
            if idx not in used_indices:
                continue
            
            try:
                doc_id = (
                        chunk.get("document_id")
                        or chunk.get("metadata", {}).get("document_id")
                )

                if doc_id is None:
                    raise KeyError("document_id")

                citation = CitationInfo(
                    document_id=doc_id,
                    document_title=chunk.get("document_title", "Unknown"),
                    filename=chunk.get("filename", chunk.get("document_title", "Unknown")),
                    chunk_index=chunk.get("chunk_index", 0),
                    text_excerpt=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                    relevance_score=chunk.get("relevance_score", 0.0)
                )
                citations.append(citation)
            except Exception as e:
                logger.warning(f"[AnalysisAgent] Failed to create citation: {str(e)}")
                continue

        return citations
