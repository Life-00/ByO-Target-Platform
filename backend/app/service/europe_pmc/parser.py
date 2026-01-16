from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.schemas.retrieval import Paper, AbstractSentence


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> List[str]:
    text = (text or "").replace("\n", " ").strip()
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if len(p.strip()) > 5]


def parse_epmc_result(
    r: Dict[str, Any],
    query_id: str,
    retrieval_reason: str,
) -> Optional[Paper]:
    """
    Europe PMC 단일 result dict -> Paper
    - Paper 스키마는 arXiv fetcher와 동일하게 채운다. 
    """
    title = (r.get("title") or "").strip()
    if not title:
        return None

    # Europe PMC는 source + id 조합이 존재
    source = (r.get("source") or "").strip()  # "MED", "PMC", "AGR", "PPR", ...
    epmc_id = (r.get("id") or "").strip()
    doi = (r.get("doi") or "").strip()

    # 내부 고유키: source:id 우선, 없으면 DOI
    paper_id = f"{source}:{epmc_id}" if (source and epmc_id) else (doi or title[:64])

    journal = (r.get("journalTitle") or r.get("journal") or "").strip() or None
    year = None
    y = (r.get("pubYear") or "").strip()
    if y.isdigit():
        year = int(y)

    abstract = (r.get("abstractText") or "").strip()
    abs_sents = [
        AbstractSentence(sentence_id=f"{paper_id}_s{i}", text=s)
        for i, s in enumerate(split_sentences(abstract))
    ]

    # URL(가능하면 Europe PMC 레코드 링크)
    url = None
    if source and epmc_id:
        url = f"https://europepmc.org/article/{source}/{epmc_id}"

    # pdf_storage_path는 여기선 아직 없음(다운로드 단계는 별도)
    return Paper(
        pmid=paper_id,
        title=title,
        journal=journal,
        year=year,
        abstract_sentences=abs_sents,
        url=url,
        source="europe_pmc",
        retrieval_reason=retrieval_reason,
        query_id=query_id,
        doi=doi or None,  # Paper 스키마에 doi가 없다면 제거해도 됨(현재 Paper는 extra=allow인 경우가 많음)
    )
