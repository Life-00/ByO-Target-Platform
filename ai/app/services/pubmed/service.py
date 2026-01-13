# app/services/pubmed/service.py
from typing import List

from app.schemas.user_query import UserQuery
from app.schemas.paper import PaperCorpus

from app.services.pubmed.client import search_pmids, fetch_medline
from app.services.pubmed.parser import parse_medline


def build_query_string(uq: UserQuery) -> str:
    terms = []
    if uq.target_hint:
        terms.append(uq.target_hint)
    if uq.disease:
        terms.append(uq.disease)
    if uq.organ:
        terms.append(uq.organ)
    return " AND ".join(terms)


def search_pubmed(uq: UserQuery) -> PaperCorpus:
    query = build_query_string(uq)
    retmax = uq.constraints.max_results if uq.constraints else 5
    pmids = search_pmids(query, retmax)
    papers = []
    for pmid in pmids:
        medline = fetch_medline(pmid)
        # 🔧 query_id 전달
        paper = parse_medline(
            pmid=pmid,
            record=medline,
            query_id=uq.query_id,
            retrieval_reason="keyword"
        )
        papers.append(paper)
    return PaperCorpus(
        query_id=uq.query_id,
        papers=papers
    )