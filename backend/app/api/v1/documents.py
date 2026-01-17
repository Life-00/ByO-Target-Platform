"""
API endpoints for document management.

Provides:
- POST /api/v1/documents/upload - Upload PDF document
- GET /api/v1/documents - List user's documents
- GET /api/v1/documents/{doc_id} - Get document details
- DELETE /api/v1/documents/{doc_id} - Delete document
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db_session
from app.schemas.document import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadRequest,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF document",
    responses={
        201: {"description": "Document uploaded successfully"},
        400: {"description": "Invalid file (size, format)"},
        401: {"description": "Unauthorized"},
        413: {"description": "File too large"},
        422: {"description": "Invalid request"},
    },
)
async def upload_document(
    file: UploadFile = File(
        ...,
        description="PDF file (max 50MB)",
    ),
    title: str = Query(..., min_length=1, max_length=255, description="Document title"),
    description: str | None = Query(
        None,
        max_length=1000,
        description="Optional description",
    ),
    session_id: str | None = Query(None, description="Associated session ID"),
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db_session)] = None,
) -> DocumentResponse:
    """
    Upload a PDF document.

    **Query Parameters:**
    - file: PDF file (multipart/form-data)
    - title: Document title (required, 1-255 chars)
    - description: Document description (optional)
    - session_id: Associated session (optional)

    **Validation:**
    - Max file size: 50MB
    - Allowed MIME types: application/pdf
    - Virus scanning: (TODO)

    **Returns:**
    - DocumentResponse with document details
    """
    # Validate file size
    file_size = 0
    file_content = b""
    
    # Read file in chunks to validate size
    max_size = 50 * 1024 * 1024  # 50MB
    
    while True:
        chunk = await file.read(1024 * 1024)  # 1MB chunks
        if not chunk:
            break
        file_size += len(chunk)
        file_content += chunk
        
        if file_size > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds 50MB limit",
            )

    # Validate MIME type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {file.content_type}. Only PDF allowed.",
        )

    # Validate file name
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF",
        )

    # Create upload request
    request = DocumentUploadRequest(
        title=title,
        description=description,
        session_id=session_id,
    )

    # Upload document
    return await DocumentService.upload_document(
        db=db,
        user_id=current_user["user_id"],
        request=request,
        file_content=file_content,
        file_name=file.filename,
        mime_type=file.content_type,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List user's documents",
    responses={
        200: {"description": "Documents retrieved"},
        401: {"description": "Unauthorized"},
    },
)
async def list_documents(
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=500, description="Max 500")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> DocumentListResponse:
    """
    Get list of user's documents with pagination.

    **Query Parameters:**
    - limit: Number of documents (1-500, default 50)
    - offset: Pagination offset (default 0)

    **Returns:**
    - DocumentListResponse with documents and total count
    """
    documents, total_count = await DocumentService.list_documents(
        db=db,
        user_id=current_user["user_id"],
        limit=limit,
        offset=offset,
    )

    return DocumentListResponse(
        documents=documents,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/session/{session_id}",
    response_model=DocumentListResponse,
    summary="List documents in a session",
    responses={
        200: {"description": "Documents retrieved"},
        401: {"description": "Unauthorized"},
    },
)
async def list_session_documents(
    session_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=500, description="Max 500")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> DocumentListResponse:
    """
    Get list of documents in a specific session.

    **Path Parameters:**
    - session_id: Session ID

    **Query Parameters:**
    - limit: Number of documents (1-500, default 50)
    - offset: Pagination offset (default 0)

    **Returns:**
    - DocumentListResponse with documents and total count for the session
    """
    documents, total_count = await DocumentService.list_session_documents(
        db=db,
        user_id=current_user["user_id"],
        session_id=session_id,
        limit=limit,
        offset=offset,
    )

    return DocumentListResponse(
        documents=documents,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    responses={
        200: {"description": "Document found"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document not found"},
    },
)
async def get_document(
    document_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentResponse:
    """
    Get a specific document by ID.

    **Path Parameters:**
    - document_id: UUID of the document

    **Returns:**
    - DocumentResponse with document details or 404 if not found
    """
    document = await DocumentService.get_document(
        db=db,
        user_id=current_user["user_id"],
        document_id=document_id,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return document


@router.get(
    "/{document_id}/download",
    summary="Download PDF document",
    responses={
        200: {"description": "File downloaded"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document not found"},
    },
)
async def download_document(
    document_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    """
    Download a PDF document.

    **Path Parameters:**
    - document_id: Document ID to download

    **Returns:**
    - File content with PDF headers or 404 if not found
    """
    from sqlalchemy import select
    from app.db.models import Document
    
    # Get document (authorization check)
    query = select(Document).where(
        (Document.id == int(document_id)) & (Document.user_id == int(current_user["user_id"]))
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Return file response
    return FileResponse(
        path=document.file_path,
        media_type="application/pdf",
        filename=document.file_name,
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete document",
    responses={
        200: {"description": "Document deleted"},
        401: {"description": "Unauthorized"},
        404: {"description": "Document not found"},
    },
)
async def delete_document(
    document_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentDeleteResponse:
    """
    Delete a document and its file.

    **Path Parameters:**
    - document_id: UUID of the document to delete

    **Returns:**
    - DocumentDeleteResponse with deletion details or 404 if not found

    **Warning:**
    - This is permanent and will delete the file and metadata
    """
    result = await DocumentService.delete_document(
        db=db,
        user_id=current_user["user_id"],
        document_id=document_id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return result
