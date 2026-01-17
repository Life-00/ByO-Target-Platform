"""
Embedding Agent Implementation

This agent is responsible for:
- Extracting text from PDF files
- Performing token-based text chunking using tokenizer
- Generating embeddings using Upstage Embedding API
- Storing embeddings in ChromaDB
- Updating the PostgreSQL database with the document's status
"""

from app.agents.base_agent import BaseAgent
from app.services.embedding_service import EmbeddingService
from app.db.models import Document
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
from pypdf import PdfReader
from .schemas import EmbeddingAgentInputSchema, EmbeddingAgentOutputSchema
from app.utils.tokenizer import chunk_text_by_tokens, count_tokens, _truncate_to_tokens


class EmbeddingAgent(BaseAgent):
    """Agent for processing PDFs and generating embeddings"""
    
    def __init__(self, db: AsyncSession = None, embedding_service: EmbeddingService = None):
        super().__init__()
        self.agent_type = "embedding_agent"
        self.db = db
        self.embedding_service = embedding_service

    async def extract_text(self, file_path: str) -> tuple[str, list[tuple[int, str]]]:
        """
        Extract text from a PDF file with page tracking.
        
        Returns:
            tuple: (full_text, page_texts)
                - full_text: All text concatenated
                - page_texts: List of (page_number, page_text) tuples
        """
        reader = PdfReader(file_path)
        full_text = ""
        page_texts = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            full_text += page_text + "\n"
            page_texts.append((page_num, page_text))
        
        return full_text, page_texts

    async def chunk_text(self, text: str, max_tokens: int = 2800, overlap_tokens: int = 150) -> list:
        """
        Split text into token-based chunks.
        
        Args:
            text: Full text to chunk
            max_tokens: Maximum tokens per chunk (default: 2800 for Upstage 4000 limit)
            overlap_tokens: Overlap between chunks for context continuity (default: 150)
            
        Returns:
            List of text chunks
        """
        chunks = chunk_text_by_tokens(
            text=text,
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens
        )
        return chunks

    async def _generate_summary(self, text: str) -> str:
        """
        Generate a summary of the PDF using LLM.
        
        Args:
            text: Full extracted text from PDF
            
        Returns:
            str: Generated summary in Korean (300-500 words)
        """
        try:
            import httpx
            from app.config import settings
            from app.agents.embedding_agent.prompt import SUMMARY_PROMPT
            
            # Truncate text to avoid token limit (2000 tokens for safety)
            # Upstage Chat API has 4096 token limit, keep margin for prompt + response
            truncated_text = _truncate_to_tokens(text, max_tokens=2000)
            token_count = count_tokens(truncated_text)
            print(f"[EmbeddingAgent] Summary input: {token_count} tokens")
            
            # Format prompt with text
            prompt = SUMMARY_PROMPT.format(text=truncated_text)
            
            # Call Upstage Chat API directly
            headers = {
                "Authorization": f"Bearer {settings.upstage_api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": "solar-1-mini-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000,
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.upstage.ai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and "choices" in data and len(data["choices"]) > 0:
                        summary = data["choices"][0].get("message", {}).get("content", "")
                        return summary.strip() if summary else ""
            
            return ""

        except Exception as e:
            print(f"[EmbeddingAgent] Failed to generate summary: {str(e)}")
            return ""

    async def process_pdf(self, document_id: int, file_path: str, max_tokens: int = 2800):
        """
        Process a PDF document: extract text, chunk it, generate embeddings, and store in ChromaDB.
        
        Args:
            document_id: Document ID in database
            file_path: Path to PDF file
            max_tokens: Maximum tokens per chunk (default: 2800)
        """
        from app.db.models import DocumentChunk
        import uuid
        
        # Extract text from PDF with page tracking
        full_text, page_texts = await self.extract_text(file_path)

        # Chunk the text (token-based)
        chunks = await self.chunk_text(full_text, max_tokens=max_tokens)

        # Map each chunk to its page number
        chunk_page_mapping = []
        char_position = 0
        
        for chunk_idx, chunk_text in enumerate(chunks):
            # Find which page this chunk starts in
            page_num = 1
            cumulative_chars = 0
            
            for page_number, page_text in page_texts:
                if char_position < cumulative_chars + len(page_text):
                    page_num = page_number
                    break
                cumulative_chars += len(page_text) + 1  # +1 for newline
            
            chunk_page_mapping.append({
                "chunk_index": chunk_idx,
                "page_number": page_num,
                "text": chunk_text,
                "char_count": len(chunk_text)
            })
            
            char_position += len(chunk_text)

        # Generate embeddings for each chunk using embed_batch
        embedding_result = await self.embedding_service.embed_batch(chunks)
        embeddings = embedding_result["embeddings"]

        # Generate summary from the first 2000 tokens of text
        summary = await self._generate_summary(full_text)

        # Store chunks in PostgreSQL with page numbers
        db_chunks = []
        for i, chunk_info in enumerate(chunk_page_mapping):
            chroma_id = str(uuid.uuid4())
            
            db_chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=chunk_info["chunk_index"],
                page_number=chunk_info["page_number"],
                text_content=chunk_info["text"],
                char_count=chunk_info["char_count"],
                chroma_id=chroma_id,
                embedding_model=self.embedding_service.model
            )
            self.db.add(db_chunk)
            db_chunks.append(db_chunk)
        
        await self.db.flush()  # Get IDs for chunks

        # Store embeddings in ChromaDB with metadata
        chroma_ids = [chunk.chroma_id for chunk in db_chunks]
        metadatas = [
            {
                "document_id": document_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "char_count": chunk.char_count,
            }
            for chunk in db_chunks
        ]
        
        # Add to ChromaDB
        await self.embedding_service.add_documents(
            ids=chroma_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        
        # Update document status in PostgreSQL
        query = select(Document).where(Document.id == document_id)
        result = await self.db.execute(query)
        document = result.scalar_one_or_none()

        if document:
            document.is_indexed = True
            document.page_count = len(page_texts)  # Actual page count
            document.summary = summary  # Store the generated summary
            await self.db.commit()

        return {
            "status": "success",
            "document_id": document_id,
            "chunk_count": len(chunks),
            "embedding_count": len(embeddings),
            "embedding_dim": self.embedding_service.embedding_dim,
            "summary": summary,
            "page_count": len(page_texts),
        }

    async def execute(self, request: EmbeddingAgentInputSchema) -> EmbeddingAgentOutputSchema:
        """
        Main execution method required by BaseAgent.
        
        Args:
            request: EmbeddingAgentInputSchema with document_id and chunk_size
        
        Returns:
            EmbeddingAgentOutputSchema with processing results
        """
        try:
            # Validate session if provided
            if request.session_id and not self.validate_session(request.session_id):
                return EmbeddingAgentOutputSchema(
                    success=False,
                    document_id=request.document_id,
                    status="failed",
                    error="Invalid session ID"
                )
            
            # Fetch document from database
            if not self.db:
                return EmbeddingAgentOutputSchema(
                    success=False,
                    document_id=request.document_id,
                    status="failed",
                    error="Database session not initialized"
                )
            
            query = select(Document).where(Document.id == request.document_id)
            result = await self.db.execute(query)
            document = result.scalar_one_or_none()

            if not document:
                return EmbeddingAgentOutputSchema(
                    success=False,
                    document_id=request.document_id,
                    status="failed",
                    error="Document not found"
                )

            # Process the PDF
            file_path = document.file_path
            result = await self.process_pdf(request.document_id, file_path, request.chunk_size)

            # Log execution
            self.log_execution(
                request.session_id or "unknown",
                "completed",
                f"Processed document {request.document_id} with {result['chunk_count']} chunks"
            )

            return EmbeddingAgentOutputSchema(
                success=True,
                document_id=result["document_id"],
                chunk_count=result["chunk_count"],
                embedding_count=result["embedding_count"],
                status=result["status"],
                data={
                    "file_path": file_path,
                    "metadata": {
                        "document_id": request.document_id,
                        "chunk_size": request.chunk_size
                    }
                }
            )

        except FileNotFoundError as e:
            error_info = await self.handle_error(e, f"File not found: {str(e)}")
            return EmbeddingAgentOutputSchema(
                success=False,
                document_id=request.document_id,
                status="failed",
                error=error_info["error_message"]
            )
        except Exception as e:
            error_info = await self.handle_error(e, "PDF processing error")
            return EmbeddingAgentOutputSchema(
                success=False,
                document_id=request.document_id,
                status="failed",
                error=error_info["error_message"]
            )
