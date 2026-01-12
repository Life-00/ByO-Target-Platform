from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# dataclasses, typing, time, xml.etree, datetime 는 파이썬 표준 라이브러리(내장)
# requests 는 외부 라이브러리(pip 설치 필요)


@dataclass
class Paper:
    pmid: str
    title: str
    journal: str
    year: str  # PubMed에서 문자열로 오기도 해서 일단 str로 받고, 출력에서 int로 변환
    authors: List[str]
    abstract: str
    url: str


class PubMedClient:
    """
    PubMed E-utilities 기반 논문 검색/수집 클라이언트.
    """
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, email: str, tool: str = "byo_target_validation"):
        self.email = email
        self.tool = tool

    def search(
        self,
        term: str,
        retmax: int = 20,
        mindate: Optional[str] = None,
        maxdate: Optional[str] = None,
    ) -> List[str]:
        params = {
            "db": "pubmed",
            "term": term,
            "retmode": "json",
            "retmax": str(retmax),
            "tool": self.tool,
            "email": self.email,
            "sort": "pub+date",  # 최신 우선
        }

        # 날짜 필터(옵션): YYYY 또는 YYYY/MM/DD
        if mindate and maxdate:
            params.update(
                {
                    "datetype": "pdat",
                    "mindate": mindate,
                    "maxdate": maxdate,
                }
            )

        r = requests.get(f"{self.BASE}/esearch.fcgi", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_details(self, pmids: List[str]) -> List[Paper]:
        if not pmids:
            return []

        chunks = [pmids[i : i + 50] for i in range(0, len(pmids), 50)]
        papers: List[Paper] = []

        for chunk in chunks:
            ids = ",".join(chunk)
            params = {
                "db": "pubmed",
                "id": ids,
                "retmode": "xml",
                "tool": self.tool,
                "email": self.email,
            }
            r = requests.get(f"{self.BASE}/efetch.fcgi", params=params, timeout=30)
            r.raise_for_status()

            root = ET.fromstring(r.text)
            for article in root.findall(".//PubmedArticle"):
                pmid = (article.findtext(".//PMID") or "").strip()
                title = (article.findtext(".//ArticleTitle") or "").strip()
                journal = (article.findtext(".//Journal/Title") or "").strip()
                year = (
                    article.findtext(".//PubDate/Year")
                    or article.findtext(".//PubDate/MedlineDate")
                    or ""
                ).strip()

                authors: List[str] = []
                for a in article.findall(".//AuthorList/Author"):
                    last = (a.findtext("LastName") or "").strip()
                    fore = (a.findtext("ForeName") or "").strip()
                    if last or fore:
                        authors.append(f"{fore} {last}".strip())

                abstract_parts: List[str] = []
                for ab in article.findall(".//Abstract/AbstractText"):
                    abstract_parts.append("".join(ab.itertext()).strip())
                abstract = "\n".join([p for p in abstract_parts if p])

                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

                papers.append(
                    Paper(
                        pmid=pmid,
                        title=title,
                        journal=journal,
                        year=year,
                        authors=authors,
                        abstract=abstract,
                        url=url,
                    )
                )

            time.sleep(0.34)  # 간단 레이트리밋(과도 요청 방지)

        return papers


class RetrieverAgent:
    """
    입력(연구 대상/질병/연구 주제)에 대한 관련 논문 탐색 및 수집.
    ✅ 팀 스키마(ai/app/schemas/paper.py)의 PaperCorpus/Paper/AbstractSentence 형태로 반환하도록 최소 수정.
    """
    def __init__(self, pubmed: PubMedClient):
        self.pubmed = pubmed

    def build_query(self, target: str, disease: Optional[str], topic: Optional[str]) -> str:
        terms = [target]
        if disease:
            terms.append(disease)
        if topic:
            terms.append(topic)
        return " AND ".join([f"({t})" for t in terms if t])

    def _year_to_int(self, year_raw: str) -> int:
        """
        PubMed year가 '2020' 또는 '2020 Jan-Feb' 같은 형태일 수 있어서,
        앞의 4자리 숫자를 뽑아 int로 변환. 실패하면 0.
        """
        if not year_raw:
            return 0
        # 앞 4자리만 숫자면 사용
        head = year_raw.strip()[:4]
        return int(head) if head.isdigit() else 0

    def _abstract_to_sentences(self, pmid: str, abstract: str) -> List[Dict[str, str]]:
        """
        ✅ team schema: AbstractSentence(sentence_id, text)
        - 최소 구현: '.' 기준으로 대충 분리 (정교한 문장분리는 추후 개선 가능)
        """
        text = (abstract or "").replace("\n", " ").strip()
        if not text:
            return []

        parts = [s.strip() for s in text.split(".") if s.strip()]
        out: List[Dict[str, str]] = []
        for i, s in enumerate(parts, 1):
            out.append(
                {
                    "sentence_id": f"{pmid}_s{i}",
                    "text": s + ".",
                }
            )
        return out

    def _make_query_id(self) -> str:
        """
        ✅ team schema: UserQuery.query_id / PaperCorpus.query_id 와 연결될 값
        - 지금은 Retriever 단독 테스트라 timestamp 기반으로 생성
        """
        return datetime.now().strftime("q_%Y%m%d_%H%M%S")

    def run(
        self,
        target: str,
        disease: Optional[str] = None,
        topic: Optional[str] = None,
        retmax: int = 25,
        recent_years_first: bool = True,
        # ✅ (선택) 팀 user_query.constraints의 year_from을 그대로 받을 수 있게 최소 확장
        year_from: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        ✅ 반환은 PaperCorpus 스키마를 우선으로 맞춤:
        {
          "query_id": "...",
          "papers": [
             {
               "pmid": "...",
               "title": "...",
               "year": 2024,
               "journal": "...",
               "abstract_sentences": [{"sentence_id":"...","text":"..."}, ...],
               "retrieval_reason": "keyword"
             }, ...
          ],

          # 아래는 디버그/개발 편의용(중앙/graph 붙일 때 유용)
          "debug": {"query": "...", "used_queries": [...]},
          "followup_request": {...} (optional)
        }
        """
        query_id = self._make_query_id()
        query = self.build_query(target, disease, topic)

        pmids: List[str] = []
        used_queries: List[Dict[str, str]] = []

        # year_from이 들어오면 mindate를 그걸로 우선(팀 스키마와 연결)
        # 없으면 기존처럼 recent_years_first 로직 사용
        if year_from is not None:
            mindate = str(year_from)
            pmids = self.pubmed.search(query, retmax=retmax, mindate=mindate, maxdate="2026")
            used_queries.append({"term": query, "mindate": mindate, "maxdate": "2026"})
        else:
            # 1차: 최근 논문 위주
            if recent_years_first:
                pmids = self.pubmed.search(query, retmax=retmax, mindate="2023", maxdate="2026")
                used_queries.append({"term": query, "mindate": "2023", "maxdate": "2026"})

            # 2차: 부족하면 기간 확장(누락 보완)
            if len(pmids) < max(8, retmax // 3):
                more = self.pubmed.search(query, retmax=retmax, mindate="2018", maxdate="2026")
                used_queries.append({"term": query, "mindate": "2018", "maxdate": "2026"})
                seen = set(pmids)
                for x in more:
                    if x not in seen:
                        pmids.append(x)
                        seen.add(x)

        raw_papers = self.pubmed.fetch_details(pmids)

        # ✅ team schema로 변환
        papers_for_schema: List[Dict[str, Any]] = []
        for p in raw_papers:
            papers_for_schema.append(
                {
                    "pmid": p.pmid,
                    "title": p.title,
                    "year": self._year_to_int(p.year),
                    "journal": p.journal,
                    "abstract_sentences": self._abstract_to_sentences(p.pmid, p.abstract),
                    "retrieval_reason": "keyword",  # 스키마 주석: keyword | synonym | update
                }
            )

        # 3차: 그래도 적으면 추가 정보 요청 메시지
        followup_request = None
        if len(papers_for_schema) < 5:
            followup_request = {
                "message": "검색 결과가 적어서 보완이 필요합니다. 아래 중 하나를 추가로 알려주세요.",
                "need": [
                    "타깃의 동의어(유전자명/단백질명/약어)",
                    "질환을 더 구체화(아형/모델/organ)",
                    "연구 맥락(기전/표현형/치료기법/실험모델: in vitro/in vivo/clinical)",
                ],
            }

        return {
            # ✅ 팀 스키마 핵심(중앙/graph/validator가 이걸 받기 좋게)
            "query_id": query_id,
            "papers": papers_for_schema,

            # ✅ 디버그/개발 편의(필요 없으면 나중에 제거 가능)
            "debug": {
                "query": query,
                "used_queries": used_queries,
            },
            "followup_request": followup_request,
        }
