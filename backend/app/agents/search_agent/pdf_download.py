"""
PDF Download Module
Handles PDF downloading and database registration
"""

import logging
import urllib.request
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

from app.agents.search_agent.schemas import PaperInfo
from app.db.models import Document
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def download_pdfs(
    papers: List[PaperInfo],
    session_id: int,
    user_id: int,
    uploads_dir: Path,
    db: AsyncSession = None,
    background_tasks: Optional[object] = None,
) -> Dict[str, List]:
    """
    Download PDFs to session-specific directory and register in DB
    
    Args:
        papers: List of papers to download
        session_id: Session ID for organizing files
        user_id: User ID
        uploads_dir: Base directory for uploads
        db: Optional database session for registration
        
    Returns:
        Dict with 'paths' (file paths) and 'document_ids' (DB IDs)
    """
    download_paths = []
    document_ids = []

    # Create session-specific directory
    session_dir = uploads_dir / str(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    for paper in papers:
        try:
            # Generate safe filename
            safe_title = "".join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_'))[:100]
            filename = f"{paper.arxiv_id}_{safe_title}.pdf"
            filepath = session_dir / filename

            logger.info(f"[PDFDownload] Downloading: {paper.pdf_url}")

            # Download PDF
            urllib.request.urlretrieve(paper.pdf_url, str(filepath))
            download_paths.append(str(filepath))

            # Register in DB if db session is available
            if db:
                try:
                    # Get file size
                    file_size = filepath.stat().st_size
                    
                    # Create document record
                    document = Document(
                        session_id=session_id,
                        user_id=user_id,
                        title=paper.title[:200],  # Truncate if too long
                        file_name=filename,
                        file_path=str(filepath),
                        file_size=file_size,
                        mime_type="application/pdf",
                        description=f"arXiv {paper.arxiv_id} - Relevance: {paper.relevance_score:.0%}",
                        summary=paper.abstract[:1000],  # Store abstract as initial summary
                        is_indexed=False,  # Not yet embedded
                        created_at=datetime.now(),
                    )
                    
                    db.add(document)
                    await db.flush()  # Get the ID
                    document_ids.append(document.id)
                    
                    logger.info(f"[PDFDownload] Registered document ID: {document.id}")
                    
                except Exception as db_error:
                    logger.error(f"[PDFDownload] DB registration failed: {str(db_error)}")
                    # Continue even if DB registration fails

            logger.info(f"[PDFDownload] Saved to: {filepath}")

        except Exception as e:
            logger.error(f"[PDFDownload] Download failed for {paper.arxiv_id}: {str(e)}")
            continue

    # Commit all document records
    if db and document_ids:
        try:
            await db.commit()
            logger.info(f"[PDFDownload] Committed {len(document_ids)} documents to DB")
            
            # Schedule auto-indexing for each downloaded document
            if background_tasks:
                from app.api.v1.documents import auto_index_document
                for doc_id in document_ids:
                    background_tasks.add_task(
                        auto_index_document,
                        document_id=doc_id,
                        user_id=user_id
                    )
                logger.info(f"[PDFDownload] Scheduled auto-indexing for {len(document_ids)} documents")
                
        except Exception as e:
            logger.error(f"[PDFDownload] DB commit failed: {str(e)}")
            await db.rollback()

    return {
        "paths": download_paths,
        "document_ids": document_ids
    }
