# app/services/pubmed/parser.py
from __future__ import annotations

from typing import List
import re

from app.schemas.retrieval import Paper, AbstractSentence, RetrievalReason


def _extract_tag(record: str, tag: str) -> str:
    for line in record.split("\n"):
        if line.startswith(tag):
            return line.replace(tag, "").strip()
    return ""


def split_sentences(text: str) -> List[str]:
    text = (text or "").replace("\n", " ")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def parse_medline(
    pmid: str,
    record: str,
    query_id: str,
    retrieval_reason: RetrievalReason = "keyword",
) -> Paper:
    """
    MEDLINE text → Paper 객체
    """
    title = _extract_tag(record, "TI  -")
    journal = _extract_tag(record, "JT  -")
    year_raw = _extract_tag(record, "DP  -")
    abstract = _extract_tag(record, "AB  -")

    year = int(year_raw[:4]) if year_raw[:4].isdigit() else None
    sentences = split_sentences(abstract)

    return Paper(
        pmid=pmid,
        title=title,
        journal=journal or None,
        year=year,
        abstract_sentences=[
            AbstractSentence(sentence_id=f"{pmid}_s{i}", text=s)
            for i, s in enumerate(sentences)
        ],
        retrieval_reason=retrieval_reason,
        query_id=query_id,
    )
