"""
Embedding Agent Implementation

Responsibilities:
- Extract text from PDF
- Split text into logical sections using LLM
- Chunk text by tokens
- Generate embeddings via EmbeddingService
- Store chunks in PostgreSQL
- Store embeddings in ChromaDB
"""

import json
import uuid
import re
from typing import List, Dict, Tuple

from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.base_agent import BaseAgent
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import get_llm_service
from app.db.models import Document, DocumentChunk
from app.utils.tokenizer import chunk_text_by_tokens, _truncate_to_tokens

from .schemas import EmbeddingAgentInputSchema, EmbeddingAgentOutputSchema
from app.agents.embedding_agent.prompt import (
    SECTION_SPLIT_SYSTEM_PROMPT,
    SECTION_SPLIT_USER_PROMPT,
    SUMMARY_PROMPT,
)


class EmbeddingAgent(BaseAgent):
    def __init__(self, db: AsyncSession = None, embedding_service: EmbeddingService = None):
        super().__init__()
        self.agent_type = "embedding_agent"
        self.db = db
        self.embedding_service = embedding_service
        self.llm_service = get_llm_service()

    # ------------------------------------------------------------------
    # 1. PDF TEXT EXTRACTION
    # ------------------------------------------------------------------
    async def extract_text(self, file_path: str) -> Tuple[str, List[Tuple[int, str]]]:
        reader = PdfReader(file_path)
        full_text = ""
        page_texts = []

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            full_text += page_text + "\n"
            page_texts.append((page_num, page_text))

        return full_text, page_texts

    # ------------------------------------------------------------------
    # 2. SECTION SPLITTING
    # ------------------------------------------------------------------
    def _safe_json_loads(self, text: str) -> List[Dict]:
        start = text.find("[")
        end = text.rfind("]")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON array found")

        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired = re.sub(r'(?<!\\)\n', '\\n', candidate)
            return json.loads(repaired)

    def _slice_text_by_titles(self, full_text: str, titles: List[str]) -> List[Dict]:
        lower_text = full_text.lower()
        positions = []

        for title in titles:
            idx = lower_text.find(title.lower())
            if idx != -1:
                positions.append((title, idx))

        positions.sort(key=lambda x: x[1])

        sections = []
        for i, (title, start) in enumerate(positions):
            end = positions[i + 1][1] if i + 1 < len(positions) else len(full_text)
            sections.append({
                "section_title": title,
                "text": full_text[start:end]
            })

        return sections

    async def split_into_sections_with_llm(self, text: str) -> List[Dict]:
        truncated = _truncate_to_tokens(text, max_tokens=3000)
        user_prompt = SECTION_SPLIT_USER_PROMPT.format(text=truncated)

        try:
            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=SECTION_SPLIT_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=1500,
            )

            content = response.get("content", "")
            parsed = self._safe_json_loads(content)

            titles = [
                item["section_title"]
                for item in parsed
                if isinstance(item, dict) and "section_title" in item
            ]

            if not titles:
                raise ValueError("No valid section titles")

            sections = self._slice_text_by_titles(text, titles)
            
            # Ensure at least one section exists
            if not sections:
                return [{"section_title": "Full Document", "text": text}]
            
            return sections

        except Exception as e:
            self.logger.warning(f"[EmbeddingAgent] Section split fallback: {e}")
            return [{"section_title": "Full Document", "text": text}]

    # ------------------------------------------------------------------
    # 3. CHUNKING
    # ------------------------------------------------------------------
    async def chunk_text(self, text: str, max_tokens: int, overlap_tokens: int = 150) -> List[str]:
        return chunk_text_by_tokens(
            text=text,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens
        )

    # ------------------------------------------------------------------
    # 4. SUMMARY
    # ------------------------------------------------------------------
    async def _generate_summary(self, text: str) -> str:
        try:
            truncated = _truncate_to_tokens(text, max_tokens=2000)
            prompt = SUMMARY_PROMPT.format(text=truncated)

            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
            )
            return response.get("content", "").strip()

        except Exception as e:
            self.logger.warning(f"[EmbeddingAgent] Summary failed: {e}")
            return ""

    # ------------------------------------------------------------------
    # 5. MAIN PIPELINE
    # ------------------------------------------------------------------
    async def process_pdf(self, document_id: int, file_path: str, max_tokens: int):
        if not self.embedding_service:
            raise RuntimeError("EmbeddingService not initialized")

        # Get document details for metadata
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Document with ID {document_id} not found")

        full_text, page_texts = await self.extract_text(file_path)
        sections = await self.split_into_sections_with_llm(full_text)

        # sections should always have at least one element due to fallback
        if not sections:
            self.logger.warning(f"[EmbeddingAgent] No sections generated, using full text")
            sections = [{"section_title": "Full Document", "text": full_text}]

        chunk_records = []
        for section_idx, section in enumerate(sections):
            chunks = await self.chunk_text(section["text"], max_tokens)
            for chunk in chunks:
                chunk_records.append({
                    "section_title": section["section_title"],
                    "section_index": section_idx,
                    "text": chunk,
                })

        if not chunk_records:
            raise ValueError("No chunks generated")

        texts = [c["text"] for c in chunk_records]
        embedding_result = await self.embedding_service.embed_batch(texts)
        embeddings = embedding_result["embeddings"]

        if len(embeddings) != len(chunk_records):
            raise ValueError("Embedding count mismatch")

        summary = await self._generate_summary(full_text)

        db_chunks = []
        for idx, record in enumerate(chunk_records):
            db_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=idx,
                page_number=1,  # TEMP: page mapping not implemented
                text_content=record["text"],
                char_count=len(record["text"]),
                chroma_id=str(uuid.uuid4()),
                embedding_model=self.embedding_service.model,
            )
            self.db.add(db_chunk)
            db_chunks.append(db_chunk)

        await self.db.flush()

        await self.embedding_service.add_documents(
            ids=[c.chroma_id for c in db_chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "document_id": document_id,
                    "chunk_index": c.chunk_index,
                    "section_title": r["section_title"],
                    "char_count": c.char_count,
                    "filename": document.file_name,
                    "document_title": document.title,
                }
                for c, r in zip(db_chunks, chunk_records)
            ],
        )

        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if document:
            document.is_indexed = True
            document.page_count = len(page_texts)
            document.summary = summary
            # Track whether section split used LLM or fallback
            section_split_used_fallback = (
                len(sections) == 1 and sections[0]["section_title"] == "Full Document"
            )
            document.section_split_confidence = (
                "fallback" if section_split_used_fallback else "llm"
            )
            await self.db.commit()

        return {
            "status": "success",
            "document_id": document_id,
            "chunk_count": len(db_chunks),
            "embedding_count": len(embeddings),
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # 6. EXECUTE
    # ------------------------------------------------------------------
    async def execute(self, request: EmbeddingAgentInputSchema) -> EmbeddingAgentOutputSchema:
        try:
            if not self.db:
                raise RuntimeError("Database session not initialized")

            result = await self.db.execute(
                select(Document).where(Document.id == request.document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                return EmbeddingAgentOutputSchema(
                    success=False,
                    document_id=request.document_id,
                    status="failed",
                    error="Document not found",
                )

            result = await self.process_pdf(
                document_id=request.document_id,
                file_path=document.file_path,
                max_tokens=request.chunk_size,
            )

            return EmbeddingAgentOutputSchema(
                success=True,
                document_id=result["document_id"],
                chunk_count=result["chunk_count"],
                embedding_count=result["embedding_count"],
                status=result["status"],
                data={"summary": result["summary"]},
            )

        except Exception as e:
            error_info = await self.handle_error(e, "PDF processing error")
            return EmbeddingAgentOutputSchema(
                success=False,
                document_id=request.document_id,
                status="failed",
                error=error_info["error_message"],
            )

