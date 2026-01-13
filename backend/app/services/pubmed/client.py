# app/services/pubmed/client.py
from typing import List
from Bio import Entrez
from app.config.env import NCBI_EMAIL

Entrez.email = NCBI_EMAIL


def search_pmids(query: str, retmax: int) -> List[str]:
    """
    PubMed 검색 → PMID 리스트
    """
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=retmax
    )
    record = Entrez.read(handle)
    return record["IdList"]


def fetch_medline(pmid: str) -> str:
    """
    PMID → MEDLINE raw text
    """
    handle = Entrez.efetch(
        db="pubmed",
        id=pmid,
        rettype="medline",
        retmode="text"
    )
    return handle.read()