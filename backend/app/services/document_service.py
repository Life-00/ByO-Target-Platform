"""
Business logic for document management.

DocumentService handles:
- Document upload and storage
- Document metadata management
- Document listing and retrieval
- Document deletion
- File system operations
"""

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Document
from app.schemas.document import (
    DocumentDeleteResponse,
    DocumentResponse,
    DocumentUploadRequest,
)

KST = ZoneInfo("Asia/Seoul")


class DocumentService:
    """Service for managing documents."""

    @staticmethod
    async def upload_document(
        db: AsyncSession,
        user_id: str,
        request: DocumentUploadRequest,
        file_content: bytes,
        file_name: str,
        mime_type: str,
    ) -> DocumentResponse:
        """
        Upload a document for user.

        Args:
            db: AsyncSession database connection
            user_id: User ID who is uploading
            request: DocumentUploadRequest with title and description
            file_content: File bytes
            file_name: Original file name
            mime_type: MIME type (e.g., application/pdf)

        Returns:
            DocumentResponse with document details
        """
        # Create upload directory if not exists
        upload_dir = Path(settings.upload_directory_abs) / str(user_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique file name
        doc_id = str(uuid4())
        file_extension = Path(file_name).suffix
        storage_file_name = f"{doc_id}{file_extension}"
        file_path = upload_dir / storage_file_name

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Create database record
        document = Document(
            user_id=int(user_id),
            session_id=int(request.session_id) if request.session_id else None,
            title=request.title,
            description=request.description,
            file_name=file_name,
            file_size=len(file_content),
            file_path=str(file_path),
            mime_type=mime_type,
            page_count=0,  # Will be updated by PDF analyzer
            is_indexed=False,
        )

        db.add(document)
        await db.flush()
        await db.commit()

        return DocumentResponse(
            id=str(document.id),
            user_id=str(document.user_id),
            session_id=str(document.session_id) if document.session_id else None,
            title=document.title,
            description=document.description,
            file_name=document.file_name,
            file_size=document.file_size,
            file_path=document.file_path,
            mime_type=document.mime_type,
            page_count=document.page_count or 0,
            chunk_count=0,
            summary=document.summary,
            is_processed=document.is_indexed,
            created_at=document.created_at.replace(tzinfo=KST) if document.created_at.tzinfo else document.created_at,
            updated_at=document.updated_at.replace(tzinfo=KST) if document.updated_at.tzinfo else document.updated_at,
        )

    @staticmethod
    async def get_document(
        db: AsyncSession,
        user_id: str,
        document_id: str,
    ) -> DocumentResponse | None:
        """
        Get a specific document by ID.

        Args:
            db: AsyncSession database connection
            user_id: User ID (for authorization check)
            document_id: Document ID to retrieve

        Returns:
            DocumentResponse or None if not found
        """
        query = select(Document).where(
            (Document.id == int(document_id)) & (Document.user_id == int(user_id))
        )
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            return None

        return DocumentResponse(
            id=str(document.id),
            user_id=str(document.user_id),
            session_id=str(document.session_id) if document.session_id else None,
            title=document.title,
            description=document.description,
            file_name=document.file_name,
            file_size=document.file_size,
            file_path=document.file_path,
            mime_type=document.mime_type,
            page_count=document.page_count or 0,
            chunk_count=0,  # TODO: Query from DocumentChunk table
            summary=document.summary,
            is_processed=document.is_indexed,
            created_at=document.created_at.replace(tzinfo=KST) if document.created_at.tzinfo else document.created_at,
            updated_at=document.updated_at.replace(tzinfo=KST) if document.updated_at.tzinfo else document.updated_at,
        )

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DocumentResponse], int]:
        """
        List user's documents with pagination.

        Args:
            db: AsyncSession database connection
            user_id: User ID to filter documents
            limit: Maximum number of documents (default 50, max 500)
            offset: Number of documents to skip

        Returns:
            Tuple of (DocumentResponse list, total count)
        """
        # Clamp limit
        limit = min(max(limit, 1), 500)

        # Get total count
        count_query = select(func.count(Document.id)).where(
            Document.user_id == int(user_id)
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get documents ordered by created_at descending
        query = (
            select(Document)
            .where(Document.user_id == int(user_id))
            .order_by(desc(Document.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        documents = result.scalars().all()

        responses = [
            DocumentResponse(
                id=str(doc.id),
                user_id=str(doc.user_id),
                session_id=str(doc.session_id) if doc.session_id else None,
                title=doc.title,
                description=doc.description,
                file_name=doc.file_name,
                file_size=doc.file_size,
                file_path=doc.file_path,
                mime_type=doc.mime_type,
                page_count=doc.page_count or 0,
                chunk_count=0,  # TODO: Count from DocumentChunk
                summary=doc.summary,
                is_processed=doc.is_indexed,
                created_at=doc.created_at.replace(tzinfo=KST) if doc.created_at.tzinfo else doc.created_at,
                updated_at=doc.updated_at.replace(tzinfo=KST) if doc.updated_at.tzinfo else doc.updated_at,
            )
            for doc in documents
        ]

        return responses, total_count

    @staticmethod
    async def list_session_documents(
        db: AsyncSession,
        user_id: str,
        session_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DocumentResponse], int]:
        """
        List documents in a specific session.

        Args:
            db: AsyncSession database connection
            user_id: User ID (for authorization)
            session_id: Session ID to filter documents
            limit: Maximum number of documents (default 50, max 500)
            offset: Number of documents to skip

        Returns:
            Tuple of (DocumentResponse list, total count)
        """
        # Clamp limit
        limit = min(max(limit, 1), 500)

        # Get total count
        count_query = select(func.count(Document.id)).where(
            (Document.session_id == session_id) & (Document.user_id == int(user_id))
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get documents ordered by created_at descending
        query = (
            select(Document)
            .where(
                (Document.session_id == session_id) & (Document.user_id == int(user_id))
            )
            .order_by(desc(Document.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        documents = result.scalars().all()

        responses = [
            DocumentResponse(
                id=str(doc.id),
                user_id=str(doc.user_id),
                session_id=str(doc.session_id) if doc.session_id else None,
                title=doc.title,
                description=doc.description,
                file_name=doc.file_name,
                file_size=doc.file_size,
                file_path=doc.file_path,
                mime_type=doc.mime_type,
                page_count=doc.page_count or 0,
                chunk_count=0,  # TODO: Count from DocumentChunk
                summary=doc.summary,
                is_processed=doc.is_indexed,
                created_at=doc.created_at.replace(tzinfo=KST) if doc.created_at.tzinfo else doc.created_at,
                updated_at=doc.updated_at.replace(tzinfo=KST) if doc.updated_at.tzinfo else doc.updated_at,
            )
            for doc in documents
        ]

        return responses, total_count

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        user_id: str,
        document_id: str,
    ) -> DocumentDeleteResponse | None:
        """
        Delete a document and its file.

        Args:
            db: AsyncSession database connection
            user_id: User ID (for authorization)
            document_id: Document ID to delete

        Returns:
            DocumentDeleteResponse with deletion details or None if not found
        """
        # Get document (authorization check)
        query = select(Document).where(
            (Document.id == int(document_id)) & (Document.user_id == int(user_id))
        )
        result = await db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            return None

        # Delete physical file
        try:
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Log error but continue with DB deletion

        # TODO: Delete from ChromaDB if processed

        # Delete from database
        await db.delete(document)
        await db.commit()

        return DocumentDeleteResponse(
            document_id=str(document_id),
            success=True,
            message="Document deleted successfully",
            timestamp=datetime.now(KST),
        )
