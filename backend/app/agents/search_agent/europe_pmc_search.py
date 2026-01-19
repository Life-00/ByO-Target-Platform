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
BIORXIV_API_BASE_URL = "https://api.biorxiv.org/pubs"


async def search_biorxiv(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Search Europe PMC for bioRxiv/medRxiv preprints and parse results.

    A minimal filter is applied first (source restriction only). If no
    results are returned, a fallback query without source restriction is tried.
    """
    try:
        page_size = max(1, min(max_results, 50))

        clean_query = query.replace("\n", " ").replace("\r", " ")
        clean_query = re.sub(r"\d+\.", "", clean_query)
        clean_query = " ".join(clean_query.split()).replace('"', "").replace("'", "")

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
                    break

        papers: List[Dict[str, Any]] = []

        for entry in results:
            try:
                title = (entry.get("title") or "").strip()
                abstract = (entry.get("abstractText") or "").strip()
                doi = (entry.get("doi") or "").strip()
                source = (entry.get("source") or "").strip().lower() or "biorxiv"
                paper_id = (entry.get("id") or doi or "").strip()
                pmcid = (entry.get("pmcid") or "").strip()
                arxiv_id = (pmcid or entry.get("acc_id") or "").strip()
                published = entry.get("firstPublicationDate") or entry.get("pubYear") or ""

                if not title or not paper_id:
                    continue

                authors = _parse_authors(entry.get("authorString"))
                pdf_url = _build_pdf_url(doi, source) or _extract_pdf_from_urls(entry)
                fulltext_xml_url = _extract_fulltext_xml_url(entry)

                if not pdf_url and not fulltext_xml_url and pmcid:
                    pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/{pmcid}.pdf"
                if not pdf_url and not fulltext_xml_url and not pmcid:
                    continue
                if not pdf_url and fulltext_xml_url:
                    pdf_url = fulltext_xml_url

                papers.append(
                    {
                        "title": title,
                        "abstract": abstract,
                        "doi": doi or paper_id,
                        "preprint_id": paper_id,
                        "source": source,
                        "arxiv_id": arxiv_id,
                        "pmcid": pmcid,
                        "authors": authors,
                        "published_date": published,
                        "pdf_url": pdf_url,
                        "fulltext_xml_url": fulltext_xml_url or "",
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
    if not author_string:
        return []
    return [author.strip() for author in author_string.split(";") if author.strip()]


def _build_pdf_url(doi: str, source: str) -> Optional[str]:
    if not doi:
        return None
    doi = doi.strip()
    if not doi:
        return None
    src = (source or "").lower()
    if src == "medrxiv":
        return f"https://www.medrxiv.org/content/{doi}.full.pdf"
    if src == "biorxiv":
        return f"https://www.biorxiv.org/content/{doi}.full.pdf"
    return None


def _extract_pdf_from_urls(entry: Dict[str, Any]) -> Optional[str]:
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


def _extract_fulltext_xml_url(entry: Dict[str, Any]) -> Optional[str]:
    urls = entry.get("fullTextUrlList", {}) or {}
    url_entries = urls.get("fullTextUrl", []) or []
    for url_entry in url_entries:
        url = url_entry.get("url")
        if not url:
            continue
        doc_style = (url_entry.get("documentStyle") or "").lower()
        if doc_style == "xml":
            return url
    return None


async def search_biorxiv_api(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """
    Fallback search using the official bioRxiv/medRxiv API (recent 30 days).
    The API is limited, so we fetch recent articles and keyword-match title/abstract locally.
    """
    try:
        page_size = min(max_results * 2, 100)
        tokens = [t.lower() for t in re.split(r"\W+", query) if len(t) > 2]
        results: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for server in ("biorxiv", "medrxiv"):
                url = f"{BIORXIV_API_BASE_URL}/{server}/30d/0"
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json() or {}
                papers = data.get("collection") or []
                for p in papers:
                    title = (p.get("preprint_title") or "").strip()
                    abstract = (p.get("preprint_abstract") or "").strip()
                    if tokens:
                        text = f"{title} {abstract}".lower()
                        if not all(tok in text for tok in tokens[:2]):
                            continue
                    doi = (p.get("biorxiv_doi") or p.get("published_doi") or "").strip()
                    if not title or not doi:
                        continue
                    pdf_url = _build_pdf_url(doi, server)
                    results.append(
                        {
                            "title": title,
                            "abstract": abstract,
                            "doi": doi,
                            "preprint_id": doi,
                            "source": server,
                            "arxiv_id": "",
                            "pmcid": "",
                            "authors": (p.get("preprint_authors") or "").split(";"),
                            "published_date": p.get("published_date") or p.get("preprint_date") or "",
                            "pdf_url": pdf_url or "",
                            "fulltext_xml_url": "",
                        }
                    )
                    if len(results) >= page_size:
                        break
                if len(results) >= page_size:
                    break
        return results[:max_results]
    except Exception as e:
        logger.error(f"[bioRxivAPI] fallback search failed: {e}")
        return []
