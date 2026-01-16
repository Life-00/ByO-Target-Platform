# app/schemas/retrieval.py
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

# 유연하게 처리
RetrievalReason = str


class AbstractSentence(BaseModel):
    sentence_id: str
    text: str


class Paper(BaseModel):
    # fetcher/pipeline에서 추가 필드가 와도 버리지 않게(보험)
    model_config = ConfigDict(extra="allow")

    pmid: str
    title: str
    year: Optional[int] = None
    journal: Optional[str] = None
    authors: List[str] = Field(default_factory=list)

    abstract_sentences: List[AbstractSentence] = Field(default_factory=list)

    retrieval_reason: RetrievalReason
    query_id: str

    pdf_storage_path: Optional[str] = None

    url: Optional[str] = None
    source: Optional[str] = None


class PaperCorpus(BaseModel):
    query_id: str
    papers: List[Paper] = Field(default_factory=list)
