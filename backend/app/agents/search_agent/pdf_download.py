"""
PDF/Fulltext Download Module
Handles PDF/XML downloading and database registration
"""

import logging
import urllib.request
import shutil
import re
from pathlib import Path
from typing import List, Dict
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
    db: AsyncSession = None
) -> Dict[str, List]:
    """
    Download PDFs (or XML fulltext) to session-specific directory and register in DB.
    """
    download_paths: List[str] = []
    document_ids: List[int] = []

    session_dir = uploads_dir / str(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    for paper in papers:
        try:
            safe_title = "".join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_'))[:100]
            raw_identifier = paper.doi or paper.preprint_id
            identifier = re.sub(r"[^\w.-]", "_", raw_identifier) if raw_identifier else "paper"
            identifier = identifier[:80]
            filename = f"{identifier}_{safe_title}.pdf"
            filepath = session_dir / filename

            pmc_id = paper.pmcid or None
            candidate_urls = []
            if paper.pdf_url:
                candidate_urls.append(paper.pdf_url)
            if pmc_id:
                candidate_urls.append(f"https://www.ebi.ac.uk/europepmc/api/pdf/{pmc_id}")
                candidate_urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf")
                candidate_urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/")
                candidate_urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/?download=1")
                candidate_urls.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc_id}/pdf/{pmc_id}.pdf")

            # Remove duplicates while preserving order
            seen = set()
            candidate_urls = [u for u in candidate_urls if not (u in seen or seen.add(u))]

            downloaded = False
            for url in candidate_urls:
                logger.info(f"[PDFDownload] Downloading: {url}")
                try:
                    request = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Referer": "https://www.biorxiv.org/",
                            "Accept": "application/pdf",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=30) as response, open(filepath, "wb") as f:
                        shutil.copyfileobj(response, f)
                    download_paths.append(str(filepath))
                    downloaded = True
                    break
                except Exception as e:
                    logger.error(f"[PDFDownload] Download failed for {url}: {str(e)}")

            # Fallback to XML fulltext if provided
            if not downloaded and paper.fulltext_xml_url:
                xml_path = filepath.with_suffix(".xml")
                try:
                    request = urllib.request.Request(
                        paper.fulltext_xml_url,
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Accept": "application/xml,text/xml",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=30) as response, open(xml_path, "wb") as f:
                        shutil.copyfileobj(response, f)
                    download_paths.append(str(xml_path))
                    filepath = xml_path
                    downloaded = True
                except Exception as e:
                    logger.error(f"[PDFDownload] XML download failed for {paper.fulltext_xml_url}: {str(e)}")

            if not downloaded:
                continue  # Skip DB registration if download failed

            # Register in DB if db session is available
            if db:
                try:
                    file_size = filepath.stat().st_size
                    mime_type = "application/xml" if filepath.suffix.lower() == ".xml" else "application/pdf"
                    document = Document(
                        session_id=session_id,
                        user_id=user_id,
                        title=paper.title[:200],
                        file_name=filepath.name,
                        file_path=str(filepath),
                        file_size=file_size,
                        mime_type=mime_type,
                        description=f"{paper.source} DOI {paper.doi} - Relevance: {paper.relevance_score:.0%}",
                        summary=paper.abstract[:1000],
                        external_id=paper.doi,
                        is_indexed=False,
                        created_at=datetime.now(),
                    )
                    db.add(document)
                    await db.flush()
                    document_ids.append(document.id)
                    logger.info(f"[PDFDownload] Registered document ID: {document.id}")
                except Exception as db_error:
                    logger.error(f"[PDFDownload] DB registration failed: {str(db_error)}")

            logger.info(f"[PDFDownload] Saved to: {filepath}")

        except Exception as e:
            logger.error(f"[PDFDownload] Download failed for {paper.preprint_id}: {str(e)}")
            continue

    if db and document_ids:
        try:
            await db.commit()
            logger.info(f"[PDFDownload] Committed {len(document_ids)} documents to DB")
        except Exception as e:
            logger.error(f"[PDFDownload] DB commit failed: {str(e)}")
            await db.rollback()

    return {"paths": download_paths, "document_ids": document_ids}
