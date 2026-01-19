# """
# Embedding Agent Implementation
#
# This agent is responsible for:
# - Extracting text from PDF files
# - Performing token-based text chunking using tokenizer
# - Generating embeddings using Upstage Embedding API
# - Storing embeddings in ChromaDB
# - Updating the PostgreSQL database with the document's status
# """
# import json
# import uuid
# import re
# from typing import List, Dict
#
# from pypdf import PdfReader
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
#
# from app.agents.base_agent import BaseAgent
# from app.services.embedding_service import EmbeddingService
# from app.services.llm_service import get_llm_service
# from app.db.models import Document, DocumentChunk
# from app.utils.tokenizer import (
#     chunk_text_by_tokens,
#     _truncate_to_tokens,
# )
#
# from .schemas import EmbeddingAgentInputSchema, EmbeddingAgentOutputSchema
# from app.agents.embedding_agent.prompt import (
#     SECTION_SPLIT_SYSTEM_PROMPT,
#     SECTION_SPLIT_USER_PROMPT,
#     SUMMARY_PROMPT,
# )
#
#
# class EmbeddingAgent(BaseAgent):
#     """Agent for processing PDFs and generating embeddings"""
#
#     def __init__(self, db: AsyncSession = None, embedding_service: EmbeddingService = None):
#         super().__init__()
#         self.agent_type = "embedding_agent"
#         self.db = db
#         self.llm_service = get_llm_service()
#         self.embedding_service = embedding_service
#
#
#     # 1. PDF TEXT EXTRACTION
#     async def extract_text(self, file_path: str) -> tuple[str, list[tuple[int, str]]]:
#         reader = PdfReader(file_path)
#         full_text = ""
#         page_texts = []
#
#         for page_num, page in enumerate(reader.pages, start=1):
#             page_text = page.extract_text() or ""
#             full_text += page_text + "\n"
#             page_texts.append((page_num, page_text))
#
#         return full_text, page_texts
#
#     def _extract_text_from_llm_response(self, response) -> str:
#         if isinstance(response.get("content"), str):
#             return response["content"]
#
#         # Case 2: response["content"] is a dict (Upstage style)
#         if isinstance(response.get("content"), dict):
#             return response["content"].get("content", "")
#
#         # Case 3: response["content"] is a list (multi-part response)
#         if isinstance(response.get("content"), list):
#             texts = []
#             for item in response["content"]:
#                 if isinstance(item, dict):
#                     if "text" in item:
#                         texts.append(item["text"])
#                     elif "content" in item:
#                         texts.append(item["content"])
#             return "\n".join(texts)
#
#         raise ValueError("Unsupported LLM response format")
#
#
#     # 2. SECTION SPLITTING (LLM 이용)
#     def _safe_json_loads(self, text: str) -> List[Dict]:
#         """
#         Robust JSON extraction & repair for LLM outputs.
#         """
#         start = text.find("[")
#         end = text.rfind("]")
#
#         if start == -1 or end == -1 or end <= start:
#             raise ValueError("No JSON array found in LLM output")
#
#         candidate = text[start:end + 1]
#
#         # 1) try normal JSON
#         try:
#             return json.loads(candidate)
#         except json.JSONDecodeError:
#             pass
#
#         # 2) repair common issues: unescaped newlines, quotes
#         repaired = candidate
#
#         # escape newlines inside strings
#         repaired = re.sub(r'(?<!\\)\n', '\\n', repaired)
#
#         # escape unescaped quotes inside text fields
#         repaired = re.sub(
#             r'"text"\s*:\s*"(.+?)"',
#             lambda m: '"text": "' + m.group(1).replace('"', '\\"') + '"',
#             repaired,
#             flags=re.DOTALL
#         )
#
#         return json.loads(repaired)
#
#     def _slice_text_by_section_titles(
#             self, full_text: str, section_titles: list[str]
#     ) -> list[dict]:
#         sections = []
#         lower_text = full_text.lower()
#
#         positions = []
#         for title in section_titles:
#             idx = lower_text.find(title.lower())
#             if idx != -1:
#                 positions.append((title, idx))
#
#         positions.sort(key=lambda x: x[1])
#
#         for i, (title, start) in enumerate(positions):
#             end = positions[i + 1][1] if i + 1 < len(positions) else len(full_text)
#             sections.append({
#                 "section_title": title,
#                 "text": full_text[start:end]
#             })
#
#         return sections
#
#
#     async def split_into_sections_with_llm(self, text: str) -> List[Dict]:
#         """
#         Split academic paper into logical sections using LLM.
#         """
#
#         truncated_text = _truncate_to_tokens(text, max_tokens=3000)
#         user_prompt = SECTION_SPLIT_USER_PROMPT.format(text=truncated_text)
#
#         try:
#             response = await self.llm_service.generate(
#                 messages=[{"role": "user", "content": user_prompt}],
#                 system_prompt=SECTION_SPLIT_SYSTEM_PROMPT,
#                 temperature=0.0,
#                 max_tokens=1500,
#             )
#
#             # content = response["content"]
#             content = self._extract_text_from_llm_response(response)
#
#             # sections = json.loads(content)
#             # sections = self._safe_json_loads(content
#
#             titles = self._safe_json_loads(content)
#             section_titles = [t["section_title"] for t in titles]
#
#             sections = self._slice_text_by_section_titles(text, section_titles)
#
#             if not isinstance(sections, list):
#                 raise ValueError("Invalid section format")
#
#             return sections
#
#         except Exception as e:
#             self.logger.warning(
#                 f"[EmbeddingAgent] Section split failed, fallback applied: {e}"
#             )
#             return [{"section_title": "Unknown", "text": text}]
#
#
#     # 3. TOKEN-BASED CHUNKING
#     async def chunk_text(self, text: str, max_tokens: int = 2800, overlap_tokens: int = 150) -> list:
#         """
#         Split text into token-based chunks.
#
#         Args:
#             text: Full text to chunk
#             max_tokens: Maximum tokens per chunk (default: 2800 for Upstage 4000 limit)
#             overlap_tokens: Overlap between chunks for context continuity (default: 150)
#
#         Returns:
#             List of text chunks
#         """
#         chunks = chunk_text_by_tokens(
#             text=text,
#             max_tokens=max_tokens,
#             overlap_tokens=overlap_tokens
#         )
#         return chunks
#
#
#     # 4. SUMMARY GENERATION
#     async def _generate_summary(self, text: str) -> str:
#         try:
#             truncated_text = _truncate_to_tokens(text, max_tokens=2000)
#             prompt = SUMMARY_PROMPT.format(text=truncated_text)
#
#             response = await self.llm_service.generate(
#                 messages=[{"role": "user", "content": prompt}],
#                 temperature=0.2,
#                 max_tokens=1000,
#             )
#
#             return response["content"].strip()
#
#         except Exception as e:
#             self.logger.warning(f"[EmbeddingAgent] Summary generation failed: {e}")
#             return ""
#
#     # 5. MAIN PIPELINE
#     async def process_pdf(self, document_id: int, file_path: str, max_tokens: int = 2800):
#
#         # 1) Extract
#         full_text, page_texts = await self.extract_text(file_path)
#
#         # 2) Section split
#         sections = await self.split_into_sections_with_llm(full_text)
#         if not sections:
#             raise ValueError("No sections generated from document")
#         self.logger.info(
#             "[TEST][SectionSplit] sections=%s",
#             [(s["section_title"], len(s["text"])) for s in sections]
#         )
#
#         # 3) Chunk per section
#         chunk_records = []
#         for section_idx, section in enumerate(sections):
#             section_chunks = await self.chunk_text(section["text"], max_tokens=max_tokens)
#
#             self.logger.info(
#                 "[TEST][Chunking] section=%s chunks=%d",
#                 section["section_title"],
#                 len(section_chunks)
#             )
#
#             for chunk_text in section_chunks:
#                 chunk_records.append({
#                     "section_title": section["section_title"],
#                     "section_index": section_idx,
#                     "text": chunk_text,
#                 })
#         if not chunk_records:
#             raise ValueError("No chunks generated from document")
#
#         # 4) Embedding
#         texts = [c["text"] for c in chunk_records]
#         embedding_result = await self.embedding_service.embed_batch(texts)
#         embeddings = embedding_result["embeddings"]
#
#         if len(embeddings) != len(chunk_records):
#             raise ValueError(
#                 f"Embedding count mismatch: {len(embeddings)} vs {len(chunk_records)}"
#             )
#
#         # 5) Summary
#         summary = await self._generate_summary(full_text)
#
#         # 6) Store chunks (PostgreSQL)
#         db_chunks = []
#         for idx, record in enumerate(chunk_records):
#             chroma_id = str(uuid.uuid4())
#             db_chunk = DocumentChunk(
#                 document_id=document_id,
#                 chunk_index=idx,
#                 page_number=1,
#                 text_content=record["text"],
#                 char_count=len(record["text"]),
#                 chroma_id=chroma_id,
#                 embedding_model=self.embedding_service.model,
#                 # section_title=record["section_title"],
#             )
#             self.db.add(db_chunk)
#             db_chunks.append(db_chunk)
#
#         await self.db.flush()
#
#         # 7. Store embeddings (ChromaDB)
#         await self.embedding_service.add_documents(
#             ids=[c.chroma_id for c in db_chunks],
#             embeddings=embeddings,
#             documents=texts,
#             metadatas=[
#                 {
#                     "document_id": document_id,
#                     "chunk_index": c.chunk_index,
#                     "section_title": r["section_title"],
#                     "char_count": c.char_count,
#                 }
#                 for c, r in zip(db_chunks, chunk_records)
#             ],
#         )
#
#         # 8. Update document
#         result = await self.db.execute(select(Document).where(Document.id == document_id))
#         document = result.scalar_one_or_none()
#
#         if document:
#             document.is_indexed = True
#             document.page_count = len(page_texts)
#             document.summary = summary
#             await self.db.commit()
#
#         return {
#             "status": "success",
#             "document_id": document_id,
#             "chunk_count": len(db_chunks),
#             "embedding_count": len(embeddings),
#             "summary": summary,
#         }
#
#
#     # 6. EXECUTE
#     async def execute(self, request: EmbeddingAgentInputSchema) -> EmbeddingAgentOutputSchema:
#         try:
#             # 1) Validate session if provided
#             if request.session_id and not self.validate_session(request.session_id):
#                 return EmbeddingAgentOutputSchema(
#                     success=False,
#                     document_id=request.document_id,
#                     status="failed",
#                     error="Invalid session ID"
#                 )
#
#             # Validate DB session
#             if not self.db:
#                 return EmbeddingAgentOutputSchema(
#                     success=False,
#                     document_id=request.document_id,
#                     status="failed",
#                     error="Database session not initialized"
#                 )
#
#             # 3) Fetch document
#             query = select(Document).where(Document.id == request.document_id)
#             result = await self.db.execute(query)
#             document = result.scalar_one_or_none()
#
#             if not document:
#                 return EmbeddingAgentOutputSchema(
#                     success=False,
#                     document_id=request.document_id,
#                     status="failed",
#                     error="Document not found"
#                 )
#
#             # 4) Process the PDF
#             file_path = document.file_path
#             result = await self.process_pdf(
#                 request.document_id,
#                 file_path,
#                 request.chunk_size
#             )
#
#             # 5) Log execution
#             self.log_execution(
#                 request.session_id or "unknown",
#                 "completed",
#                 f"Processed document {request.document_id} with {result['chunk_count']} chunks"
#             )
#
#             # 6) Return response
#             return EmbeddingAgentOutputSchema(
#                 success=True,
#                 document_id=result["document_id"],
#                 chunk_count=result["chunk_count"],
#                 embedding_count=result["embedding_count"],
#                 status=result["status"],
#                 data={
#                     "file_path": file_path,
#                     "metadata": {
#                         "document_id": request.document_id,
#                         "chunk_size": request.chunk_size
#                     }
#                 }
#             )
#
#         except FileNotFoundError as e:
#             error_info = await self.handle_error(e, f"File not found: {str(e)}")
#             return EmbeddingAgentOutputSchema(
#                 success=False,
#                 document_id=request.document_id,
#                 status="failed",
#                 error=error_info["error_message"]
#             )
#         except Exception as e:
#             error_info = await self.handle_error(e, "PDF processing error")
#             return EmbeddingAgentOutputSchema(
#                 success=False,
#                 document_id=request.document_id,
#                 status="failed",
#                 error=error_info["error_message"]
#             )

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

            return self._slice_text_by_titles(text, titles)

        except Exception as e:
            self.logger.warning(f"[EmbeddingAgent] Section split fallback: {e}")
            return [{"section_title": "Unknown", "text": text}]

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

        full_text, page_texts = await self.extract_text(file_path)
        sections = await self.split_into_sections_with_llm(full_text)

        if not sections:
            raise ValueError("No sections generated")

        section_split_used_fallback = (
                len(sections) == 1 and sections[0]["section_title"] == "Unknown"
        )

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

        try:
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

                # 섹션 분해 신뢰도 기록
                document.section_split_confidence = (
                    "fallback" if section_split_used_fallback else "llm"
                )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

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
