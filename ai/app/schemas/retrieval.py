# schemas/retrieval.py
# Retriever 출력
# vector DB에는 넣지 말고, Extractor의 입력 raw로만 사용
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


RetrievalReason = Literal["keyword", "synonym", "update", "citation_chain", "manual"]


class AbstractSentence(BaseModel):
    sentence_id: str
    text: str


class Paper(BaseModel):
    pmid: str
    title: str
    year: Optional[int] = None
    journal: Optional[str] = None

    abstract_sentences: List[AbstractSentence] = Field(default_factory=list)

    retrieval_reason: RetrievalReason
    query_id: str


class PaperCorpus(BaseModel):
    """
    Retriever가 모은 raw 후보 논문 집합.
    """
    query_id: str
    papers: List[Paper] = Field(default_factory=list)
