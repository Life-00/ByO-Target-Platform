"""
Europe PMC Search Module
Handles Europe PMC API search for bioRxiv/medRxiv preprints and result parsing
"""

import logging
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

EUROPE_PMC_API_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


async def search_biorxiv(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Search Europe PMC for bioRxiv/medRxiv preprints and parse results.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to fetch
        
    Returns:
        List of paper dictionaries with title, abstract, ids, authors, etc.
    """
    try:
        # Limit page size to avoid excessively large queries
        page_size = max(1, min(max_results, 50))
        search_query = f"({query}) AND (SRC:BIORXIV OR SRC:MEDRXIV)"
        params = {"query": search_query, "format": "json", "pageSize": page_size}

        logger.info(f"[EuropePMC] Fetching: {search_query}")

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(EUROPE_PMC_API_BASE_URL, params=params)
            response.raise_for_status()

        data = response.json()
        results = data.get("resultList", {}).get("result", []) or []

        papers: List[Dict[str, Any]] = []

        for entry in results:
            try:
                title = (entry.get("title") or "").strip()
                abstract = (entry.get("abstractText") or "").strip()
                doi = (entry.get("doi") or "").strip()
                source = (entry.get("source") or "").strip().lower() or "biorxiv"
                paper_id = (entry.get("id") or doi or "").strip()
                published = (
                    entry.get("firstPublicationDate")
                    or entry.get("pubYear")
                    or ""
                )

                # Skip if we lack identifiers or title
                if not title or not paper_id:
                    continue

                authors = _parse_authors(entry.get("authorString"))
                pdf_url = _build_pdf_url(doi, source) or _extract_pdf_from_urls(entry)

                # If no PDF URL is available, skip entry
                if not pdf_url:
                    continue

                papers.append(
                    {
                        "title": title,
                        "abstract": abstract,
                        "doi": doi or paper_id,
                        "preprint_id": paper_id,
                        "source": source,
                        "authors": authors,
                        "published_date": published,
                        "pdf_url": pdf_url,
                    }
                )

            except Exception as parse_err:
                logger.warning(f"[EuropePMC] Failed to parse entry: {parse_err}")
                continue

        logger.info(f"[EuropePMC] Parsed {len(papers)} papers from Europe PMC")
        return papers

    except Exception as e:
        logger.error(f"[EuropePMC] Search failed: {str(e)}")
        return []


def _parse_authors(author_string: Optional[str]) -> List[str]:
    """Parse author string ('A; B; C') into list."""
    if not author_string:
        return []
    return [author.strip() for author in author_string.split(";") if author.strip()]


def _build_pdf_url(doi: str, source: str) -> Optional[str]:
    """Construct PDF URL from DOI and source if possible."""
    if not doi:
        return None
    doi = doi.strip()
    if not doi:
        return None
    if source.lower() == "medrxiv":
        return f"https://www.medrxiv.org/content/{doi}.full.pdf"
    # Default to bioRxiv
    return f"https://www.biorxiv.org/content/{doi}.full.pdf"


def _extract_pdf_from_urls(entry: Dict[str, Any]) -> Optional[str]:
    """Fallback: pull PDF link from Europe PMC fullTextUrlList."""
    urls = entry.get("fullTextUrlList", {}) or {}
    url_entries = urls.get("fullTextUrl", []) or []
    for url_entry in url_entries:
        url = url_entry.get("url")
        if not url:
            continue
        doc_style = (url_entry.get("documentStyle") or "").lower()
        if "pdf" in doc_style or url.lower().endswith(".pdf"):
            return url
    return None
