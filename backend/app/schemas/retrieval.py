# app/schemas/retrieval.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

RetrievalReason = str

# abstract
class AbstractSentence(BaseModel):
    sentence_id: str
    text: str

# full-text
class SectionSentence(BaseModel):
    sentence_id: str
    text: str
    section: Optional[str] = None  # results, methods, discussion, etc.

class Paper(BaseModel):
    source: Literal["pubmed", "europe_pmc", "crossref", "arxiv", "manual"] = "pubmed"
    source_id: str = ""
    pmid: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    license: Optional[str] = None

    has_fulltext: bool = False
    title: str
    year: Optional[int] = None
    journal: Optional[str] = None
    authors: List[str] = Field(default_factory=list)

    abstract_sentences: List[AbstractSentence] = Field(default_factory=list)
    fulltext_sentences: List[SectionSentence] = Field(default_factory=list) # full-text

    retrieval_reason: RetrievalReason
    query_id: str

    @property
    def uid(self) -> str:
        return self.pmid or self.doi or self.source_id


class PaperCorpus(BaseModel):
    query_id: str
    papers: List[Paper] = Field(default_factory=list)