"""
arXiv Search Module
Handles arXiv API search and XML parsing
"""

import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

ARXIV_API_BASE_URL = "http://export.arxiv.org/api/query"


async def search_arxiv(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Search arXiv API and parse results
    
    Args:
        query: Search query string
        max_results: Maximum number of results to fetch
        
    Returns:
        List of paper dictionaries with title, abstract, arxiv_id, authors, etc.
    """
    try:
        # URL encode the query
        encoded_query = urllib.parse.quote(query)
        url = f"{ARXIV_API_BASE_URL}?search_query=all:{encoded_query}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"

        logger.info(f"[ArxivSearch] Fetching from arXiv: {url}")

        # Fetch from arXiv API
        with urllib.request.urlopen(url, timeout=30) as response:
            xml_data = response.read().decode('utf-8')

        # Parse XML
        root = ET.fromstring(xml_data)
        namespace = {'atom': 'http://www.w3.org/2005/Atom'}

        papers = []
        for entry in root.findall('atom:entry', namespace):
            try:
                title = entry.find('atom:title', namespace).text.strip()
                abstract = entry.find('atom:summary', namespace).text.strip()
                arxiv_id = entry.find('atom:id', namespace).text.split('/abs/')[-1]
                published = entry.find('atom:published', namespace).text[:10]

                # Get authors
                authors = []
                for author in entry.findall('atom:author', namespace):
                    name = author.find('atom:name', namespace)
                    if name is not None:
                        authors.append(name.text)

                # PDF URL
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                papers.append({
                    "title": title,
                    "abstract": abstract,
                    "arxiv_id": arxiv_id,
                    "authors": authors,
                    "published_date": published,
                    "pdf_url": pdf_url
                })

            except Exception as e:
                logger.warning(f"[ArxivSearch] Failed to parse entry: {str(e)}")
                continue

        logger.info(f"[ArxivSearch] Parsed {len(papers)} papers from arXiv")
        return papers

    except Exception as e:
        logger.error(f"[ArxivSearch] arXiv search failed: {str(e)}")
        return []
