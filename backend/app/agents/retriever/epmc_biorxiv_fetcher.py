from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from app.agents.retriever.types import ExpandedQuery
from app.schemas.retrieval import Paper

from app.services.europe_pmc.service import search_epmc_as_papers
from app.services.biorxiv.client import BioRxivClient
from app.services.biorxiv.parser import extract_pdf_url_from_biorxiv_details


# -----------------------------
# Helpers
# -----------------------------
_PUBMED_TAGS = re.compile(r"\[[^\]]+\]")  # e.g., [Filter], [MeSH Terms], [Title/Abstract] etc.
_WS = re.compile(r"\s+")


def sanitize_for_epmc(q: str) -> str:
    """
    QueryExpander가 PubMed 문법을 섞어 내보내는 경우가 있어서,
    Europe PMC에서 0 hitCount가 나오는 걸 방지하기 위한 최소 sanitize.
    """
    q = (q or "").strip()
    if not q:
        return q

    # PubMed field tags 제거
    q = _PUBMED_TAGS.sub("", q)

    # 흔히 들어갈 수 있는 PubMed filter phrase 제거/완화
    q = q.replace('"free full text"', "")
    q = q.replace("'free full text'", "")

    # 공백 정리
    q = _WS.sub(" ", q).strip()
    return q


def looks_like_biorxiv(r0: dict) -> bool:
    """
    Europe PMC raw result에서 biorxiv 성격을 최대한 안전하게 판별.
    - journalTitle에 'biorxiv'가 있거나
    - source가 preprint 계열(PPR 등)인 경우
    """
    jt = (r0.get("journalTitle") or r0.get("journal") or "").lower()
    src = (r0.get("source") or "").upper().strip()
    if "biorxiv" in jt:
        return True
    if src in {"PPR"}:  # Europe PMC에서 preprint가 PPR로 오는 케이스가 있음
        return True
    return False


class EuropePMCBioRxivFetcher:
    """
    RetrieverPipeline이 기대하는 인터페이스:
      - collect_pmids(...)
      - fetch_and_parse(...)
    를 그대로 제공한다.

    전략:
      1) Europe PMC에서 검색 결과를 받아 Paper로 파싱(abstract 포함)
      2) 결과 중 DOI가 있고 bioRxiv 성격이면 bioRxiv API로 url/pdf 등을 보강
      3) collect 단계에서 Paper를 캐시해두고 fetch에서 재구성하지 않음(누락/품질저하 방지)
    """

    def __init__(self, default_retmax: int = 200, debug: bool = True):
        self.default_retmax = default_retmax
        self.debug = debug

        self.biorxiv = BioRxivClient()

        # collect 단계 캐시
        self._raw_by_pid: Dict[str, List[dict]] = {}
        self._paper_by_pid: Dict[str, Paper] = {}

    def collect_pmids(
        self,
        expanded_queries: List[ExpandedQuery],
        retmax: Optional[int] = None,
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        n = retmax or self.default_retmax

        # ExpandedQuery -> (qid, qstr, reason)
        qtriples: List[Tuple[str, str, str]] = []
        for q in expanded_queries:
            qid = str(q.get("query_id") or "").strip()
            qstr = str(q.get("query") or "").strip()
            reason = str(q.get("reason") or "keyword").strip()
            if not qid or not qstr:
                continue

            qstr = sanitize_for_epmc(qstr)
            if qstr:
                qtriples.append((qid, qstr, reason))

        if self.debug:
            print(f"[EPMC+bioRxiv] collect_pmids: queries={len(qtriples)} retmax_per_query={n}")

        pmids_by_query, raw_by_pid, papers = search_epmc_as_papers(qtriples, retmax_per_query=n)

        # 캐시 저장
        self._raw_by_pid = raw_by_pid
        self._paper_by_pid = {p.pmid: p for p in papers}

        # provenance 생성 (paper_id -> [query_id...])
        prov: Dict[str, List[str]] = {}
        for qid, ids in pmids_by_query.items():
            for pid in ids:
                prov.setdefault(pid, []).append(qid)

        if self.debug:
            total_ids = sum(len(v) for v in pmids_by_query.values())
            unique_ids = len(prov)
            print(f"[EPMC+bioRxiv] collect_pmids: total_ids={total_ids} unique_ids={unique_ids}")

        return pmids_by_query, prov

    def fetch_and_parse(
        self,
        expanded_queries: List[ExpandedQuery],
        pmid_provenance: Dict[str, List[str]],
    ) -> List[Paper]:
        """
        collect에서 이미 Paper를 만들었기 때문에,
        여기서는 provenance 기반으로 query_id/reason을 대표값으로 재세팅하고,
        bioRxiv 보강(enrich)만 한다.
        """
        # qid -> reason
        q_reason: Dict[str, str] = {}
        for q in expanded_queries:
            qid = str(q.get("query_id") or "").strip()
            if not qid:
                continue
            q_reason[qid] = str(q.get("reason") or "keyword").strip()

        papers: List[Paper] = []

        if self.debug:
            print(f"[EPMC+bioRxiv] fetch_and_parse: pids={len(pmid_provenance)}")

        for pid in sorted(pmid_provenance.keys()):
            qids = pmid_provenance.get(pid) or []
            rep_qid = qids[0] if qids else "keyword"
            reason = q_reason.get(rep_qid, "keyword")

            # 1) collect에서 만든 Paper를 우선 사용
            p = self._paper_by_pid.get(pid)
            if p is None:
                # fallback: raw로라도 구성 시도
                raws = self._raw_by_pid.get(pid) or []
                if not raws:
                    continue
                r0 = raws[0]

                title = (r0.get("title") or "").strip()
                abstract = (r0.get("abstractText") or "").strip()
                journal = (r0.get("journalTitle") or r0.get("journal") or "").strip() or None
                year = None
                y = (r0.get("pubYear") or "").strip()
                if y.isdigit():
                    year = int(y)

                from app.services.europe_pmc.parser import split_sentences
                from app.schemas.retrieval import AbstractSentence

                abs_sents = [
                    AbstractSentence(sentence_id=f"{pid}_s{i}", text=s)
                    for i, s in enumerate(split_sentences(abstract))
                ]

                src_raw = (r0.get("source") or "").strip().lower() or "europe_pmc"
                url = None
                if r0.get("id") and r0.get("source"):
                    url = f"https://europepmc.org/article/{r0.get('source')}/{r0.get('id')}"

                p = Paper(
                    pmid=pid,
                    title=title,
                    journal=journal,
                    year=year,
                    abstract_sentences=abs_sents,
                    url=url,
                    source=src_raw,
                    retrieval_reason=reason,
                    query_id=rep_qid,
                )

            # 2) provenance에 맞게만 덮어쓰기
            # (Pydantic model이면 attribute set 가능 / frozen이면 copy(update=...)로 바꿔야 함)
            try:
                p.query_id = rep_qid
                p.retrieval_reason = reason
            except Exception:
                # Pydantic이 immutable인 경우 방어
                pass

            # 3) raw 기반 source/doi 확보
            raws = self._raw_by_pid.get(pid) or []
            r0 = raws[0] if raws else {}
            raw_source = (r0.get("source") or "").strip().lower()
            if raw_source:
                p.source = raw_source

            doi = (r0.get("doi") or "").strip()

            # 4) bioRxiv enrichment
            # - DOI가 있고
            # - biorxiv로 보이면
            if doi and looks_like_biorxiv(r0):
                try:
                    details = self.biorxiv.details(doi, server="biorxiv")
                    pdf_or_landing = extract_pdf_url_from_biorxiv_details(details)
                    if pdf_or_landing:
                        p.url = pdf_or_landing
                        p.source = "biorxiv"
                        if self.debug:
                            print(f"[EPMC+bioRxiv] enrich ok: pid={pid} doi={doi}")
                except Exception as e:
                    if self.debug:
                        print(f"[EPMC+bioRxiv] enrich fail: pid={pid} doi={doi} err={e}")

            papers.append(p)

        if self.debug:
            print(f"[EPMC+bioRxiv] fetch_and_parse: papers_out={len(papers)}")

        return papers
