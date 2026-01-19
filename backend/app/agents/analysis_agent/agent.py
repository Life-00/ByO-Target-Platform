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

    # -------------------------------------------------
    # Retrieval
    # -------------------------------------------------
    async def _retrieve_relevant_chunks(
            self,
            query: str,
            document_ids: List[int],
            top_k: int,
            min_score: float,
    ) -> List[Dict[str, Any]]:

        collection = self._get_chroma_collection()

        if collection is None:
            self.logger.warning(
                "[AnalysisAgent] No ChromaDB collection, skip retrieval"
            )
            return []

        embedding = (await self.embedding_service.embed(query))["embedding"]

        results = collection.query(
            query_embeddings=[embedding],
            n_results=top_k * len(document_ids),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for i, meta in enumerate(results["metadatas"][0]):
            if meta.get("document_id") in document_ids:
                score = 1 / (1 + results["distances"][0][i])
                if score < min_score:  # 🔧 [MODIFIED]
                    continue

                chunks.append({
                    "text": results["documents"][0][i],
                    "document_id": meta["document_id"],
                    "chunk_index": meta.get("chunk_index"),
                    "page_number": meta.get("page_number"),
                    "section_title": meta.get("section_title"),
                    "relevance_score": score,
                })

        chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
        return chunks[:top_k]

    # -------------------------------------------------
    # Query Rewrite
    # -------------------------------------------------
    async def _rewrite_query_with_llm(
            self,
            original_query: str,
            failure_reasons: List[str],
    ) -> str:
        prompt = f"""
        기존 질문: {original_query}
        검색 실패 사유: {failure_reasons}

        문서 근거를 더 잘 찾을 수 있도록
        질문을 더 구체적으로 한 문장으로 재작성하라.
        """

        response = await self.llm_service.generate(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=128,
        )
        return response["content"].strip()

    # -------------------------------------------------
    # Metadata Enrichment
    # -------------------------------------------------
    async def _enrich_chunks_with_metadata(self, chunks):
        doc_ids = {c["document_id"] for c in chunks}
        result = await self.db.execute(
            select(Document).where(Document.id.in_(doc_ids))
        )
        docs = {d.id: d for d in result.scalars().all()}

        enriched = []
        for c in chunks:
            base = dict(c)
            doc = docs.get(c["document_id"])
            if doc:
                base["document_title"] = doc.title
                base["document_filename"] = doc.file_name
            enriched.append(base)  # 🔧 [MODIFIED: 버그 수정]

        return enriched

    # -------------------------------------------------
    # Answer Generation
    # -------------------------------------------------
    async def _generate_answer(self, question, goal, chunks):
        context = []
        for i, c in enumerate(chunks, 1):
            doc_title = c.get("document_title") or f"Document {c.get('document_id')}"
            page = c.get("page_number", "N/A")

            context.append(
                f"[{i}] {doc_title} p.{page}\n{c['text']}"
            )

        prompt = ANALYSIS_PROMPT.format(
            analysis_goal=goal or "일반 분석",
            question=question,
            context_chunks="\n---\n".join(context),
        )

        response = await self.llm_service.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=self.system_prompt,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
        )

        # citation index 추출
        used_indices = {
            int(i) - 1
            for i in __import__("re").findall(r"\[(\d+)\]", response["content"])
        }

        return response["content"], response["usage"]["total_tokens"], used_indices

    # -------------------------------------------------
    # Citation (답변 출처 구조화)
    # -------------------------------------------------
    def _extract_citations(self, chunks, used_indices):
        citations = []
        for idx in used_indices:
            c = chunks[idx]

            doc_title = c.get("document_title") or f"Document {c.get('document_id')}"
            page = c.get("page_number", None)

            citations.append(
                CitationInfo(
                    document_id=c["document_id"],
                    document_title=doc_title,
                    page_number=page,
                    chunk_index=c.get("chunk_index"),
                    text_excerpt=c["text"][:200],
                    relevance_score=c.get("relevance_score"),
                )
            )
        return citations


    async def execute(self, request: AnalysisAgentRequest) -> AnalysisAgentResponse:

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

            # Step 2: Retrieve relevant chunks from ChromaDB + ReAct loop
            MAX_REACT_ATTEMPTS = 5  # 무한 루프 방지
            current_query = request.content
            current_top_k = request.top_k
            relevant_chunks: List[Dict[str, Any]] = []
            last_gate_result = None

            for attempt in range(MAX_REACT_ATTEMPTS):
                logger.info(f"[AnalysisAgent][ReAct] Attempt {attempt + 1}")

                # 1. Retrieve
                relevant_chunks = await self._retrieve_relevant_chunks(
                    query=current_query,
                    document_ids=document_ids,
                    top_k=current_top_k,
                    min_score=request.min_relevance_score,
                )

                if not relevant_chunks:
                    logger.info("[AnalysisAgent][ReAct] No chunks retrieved")
                    break

                evidence_items = [
                    EvidenceItem(
                        content=chunk["text"],
                        metadata={
                            "document_id": chunk.get("document_id"),
                            "section_title": chunk.get("section_title"),
                            "page_number": chunk.get("page_number"),
                        }
                    )
                    for chunk in relevant_chunks
                ]

                # 2. ReAct Gate
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

                # Act
                if gate_result.next_action == "increase_top_k":
                    current_top_k += gate_result.action_params.get("top_k_delta", 5)

                elif gate_result.next_action == "rewrite_query":
                    current_query = await self._rewrite_query_with_llm(
                        request.content,
                        gate_result.failure_reasons,
                    )

                elif gate_result.next_action == "stop":
                    break

            # ReAct 최종 실패 → 답변 생성 차단
            if not relevant_chunks or not last_gate_result or not last_gate_result.accept:
                return AnalysisAgentResponse(
                    success=True,
                    answer="선택된 문서에서 질문에 답할 충분한 근거를 찾지 못했습니다.\n\n",
                    citations=[],
                    # documents_analyzed=len(document_ids),
                    # chunks_retrieved=len(relevant_chunks),
                    metadata={
                        "react_attempts": attempt + 1,
                        "react_confidence": getattr(last_gate_result, "confidence", None),
                        "react_rationale": getattr(last_gate_result, "rationale", None),
                    }
                )


            # Step 3: Enrich chunks with document metadata
            enriched_chunks = await self._enrich_chunks_with_metadata(relevant_chunks)


            # Step 4: Generate answer using LLM (gate 통과 시만)
            answer, tokens_used, used_indices = await self._generate_answer(
                request.content,
                request.analysis_goal,
                enriched_chunks,
            )

            # citation fallback
            if not used_indices:
                logger.info(
                    "[AnalysisAgent] No explicit citation indices found, "
                    "fallback to top-ranked chunks"
                )
                used_indices = set(range(min(len(enriched_chunks), request.top_k)))

            citations = self._extract_citations(enriched_chunks, used_indices)

            return AnalysisAgentResponse(
                success=True,
                answer=answer,
                citations=citations,
                documents_analyzed=len(document_ids),
                chunks_retrieved=len(enriched_chunks),
                tokens_used=tokens_used,
                metadata={
                    "react_attempts": attempt + 1,
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"[AnalysisAgent] Error: {str(e)}")
            return AnalysisAgentResponse(
                success=False,
                answer="분석 중 오류가 발생했습니다.",
                error=str(e)
            )

