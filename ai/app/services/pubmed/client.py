# app/services/pubmed/client.py
from __future__ import annotations

import os
import time
from typing import List, Optional, Callable, TypeVar

from Bio import Entrez
from app.config.env import NCBI_EMAIL, NCBI_TOOL

T = TypeVar("T")

Entrez.email = NCBI_EMAIL
Entrez.tool = NCBI_TOOL

def _with_retry(fn: Callable[[], T], retries: int = 3, base_sleep: float = 0.4) -> T:
    """
    간단 backoff 재시도 유틸.
    - PubMed/Entrez는 일시적인 네트워크/429/5xx 등이 날 수 있으므로 service 레이어에서 처리하는 게 안전.
    """
    last_err: Optional[Exception] = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            # backoff: 0.4, 0.8, 1.6 ...
            time.sleep(base_sleep * (2 ** i))
    assert last_err is not None
    raise last_err


def search_pmids(query: str, retmax: int) -> List[str]:
    """
    PubMed 검색 → PMID 리스트
    """
    def _call():
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=retmax,
            api_key=NCBI_API_KEY or None,
        )
        try:
            record = Entrez.read(handle)
            return record.get("IdList", []) or []
        finally:
            try:
                handle.close()
            except Exception:
                pass

    return _with_retry(_call)


def fetch_medline(pmid: str) -> str:
    """
    PMID → MEDLINE raw text
    """
    def _call():
        handle = Entrez.efetch(
            db="pubmed",
            id=pmid,
            rettype="medline",
            retmode="text",
            api_key=NCBI_API_KEY or None,
        )
        try:
            return handle.read()
        finally:
            try:
                handle.close()
            except Exception:
                pass

    return _with_retry(_call)
