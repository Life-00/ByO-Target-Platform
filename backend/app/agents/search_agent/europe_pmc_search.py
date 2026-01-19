"""
Europe PMC Search Module
Handles Europe PMC API search for bioRxiv/medRxiv preprints and result parsing.
"""

import logging
import re
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)

EUROPE_PMC_API_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


async def search_biorxiv(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Search Europe PMC for bioRxiv/medRxiv preprints and parse results.

    A minimal filter is applied first (source restriction only). If no
    results are returned, a fallback query without source restriction is tried.
    This avoids over-restrictive filters (e.g., OPEN_ACCESS) that can yield zero hits.
    """
    try:
        page_size = max(1, min(max_results, 50))

        # Normalize user query to keep it loose enough
        clean_query = query.replace("\n", " ").replace("\r", " ")
        clean_query = re.sub(r"\d+\.", "", clean_query)
        clean_query = " ".join(clean_query.split()).replace('"', "").replace("'", "")

        # Primary + fallback queries
        primary_query = f"({clean_query}) AND (SRC:BIORXIV OR SRC:MEDRXIV)"
        queries = [primary_query, f"({clean_query})"]

        results: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for idx, search_query in enumerate(queries):
                params = {"query": search_query, "format": "json", "pageSize": page_size}
                logger.info(f"[EuropePMC] Fetching (attempt {idx + 1}): {search_query}")

                response = await client.get(EUROPE_PMC_API_BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()
                results = data.get("resultList", {}).get("result", []) or []
                if results:
                    break  # Stop after first successful retrieval

        papers: List[Dict[str, Any]] = []

        for entry in results:
            try:
                title = (entry.get("title") or "").strip()
                abstract = (entry.get("abstractText") or "").strip()
                doi = (entry.get("doi") or "").strip()
                source = (entry.get("source") or "").strip().lower() or "biorxiv"
                paper_id = (entry.get("id") or doi or "").strip()
                arxiv_id = (entry.get("pmcid") or entry.get("acc_id") or "").strip()
                published = entry.get("firstPublicationDate") or entry.get("pubYear") or ""

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
                        "arxiv_id": arxiv_id,
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
