# app/schemas/retrieval.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ❌ 기존: RetrievalReason = Literal["keyword", "synonym", "update", "citation_chain", "manual"]
# ✅ 수정: 그냥 문자열(str)로 변경하여 유연하게 처리
RetrievalReason = str

class AbstractSentence(BaseModel):
    sentence_id: str
    text: str

class Paper(BaseModel):
    pmid: str
    title: str
    year: Optional[int] = None
    journal: Optional[str] = None
    authors: List[str] = Field(default_factory=list)

    abstract_sentences: List[AbstractSentence] = Field(default_factory=list)

    retrieval_reason: RetrievalReason # 이제 어떤 문자열이든 OK
    query_id: str

class PaperCorpus(BaseModel):
    query_id: str
    papers: List[Paper] = Field(default_factory=list)