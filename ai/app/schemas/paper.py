# Retriever + PubMed Service 출력의 표준 형태

from pydantic import BaseModel
from typing import List


class AbstractSentence(BaseModel):
    sentence_id: str
    text: str


class Paper(BaseModel):
    pmid: str
    title: str
    year: int
    journal: str
    abstract_sentences: List[AbstractSentence]
    retrieval_reason: str  # keyword | synonym | update


class PaperCorpus(BaseModel):
    query_id: str
    papers: List[Paper]
