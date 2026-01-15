# app/schemas/retrieval.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# ??旮办〈: RetrievalReason = Literal["keyword", "synonym", "update", "citation_chain", "manual"]
# ???橃爼: 攴鸽儱 氍胳瀽??str)搿?氤€瓴巾晿???犾棸?橁矊 觳橂Μ
RetrievalReason = str


class AbstractSentence(BaseModel):
    sentence_id: str
    text: str


class Paper(BaseModel):
    source: Literal["pubmed", "europe_pmc", "crossref", "arxiv"] = "pubmed"
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

    retrieval_reason: RetrievalReason  # ?挫牅 ?措枻 氍胳瀽?挫澊??OK
    query_id: str

    @property
    def uid(self) -> str:
        return self.pmid or self.doi or self.source_id


class PaperCorpus(BaseModel):
    query_id: str
    papers: List[Paper] = Field(default_factory=list)
