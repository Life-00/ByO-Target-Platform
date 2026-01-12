from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

@dataclass
class Paper:
    pmid: str
    title: str
    journal: str
    year: str
    authors: List[str]
    abstract: str
    url: str


class PubMedClient:
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
            "sort": "pub+date",
        }

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

            time.sleep(0.34)

        return papers


class RetrieverAgent:
    """
    ✅ team schema(ai/app/schemas/paper.py) 반환만 "엄격하게" 맞추는 최소 수정 버전
    반환 형태:
    {
      "query_id": str,
      "papers": List[{
         "pmid": str,
         "title": str,
         "year": int,
         "journal": str,
         "abstract_sentences": List[{"sentence_id": str, "text": str}],
         "retrieval_reason": str
      }]
    }
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
        if not year_raw:
            return 0
        head = year_raw.strip()[:4]
        return int(head) if head.isdigit() else 0

    def _abstract_to_sentences(self, pmid: str, abstract: str) -> List[Dict[str, str]]:
        text = (abstract or "").replace("\n", " ").strip()
        if not text:
            return []

        parts = [s.strip() for s in text.split(".") if s.strip()]
        out: List[Dict[str, str]] = []
        for i, s in enumerate(parts, 1):
            out.append({"sentence_id": f"{pmid}_s{i}", "text": s + "."})
        return out

    def _make_query_id(self) -> str:
        return datetime.now().strftime("q_%Y%m%d_%H%M%S")

    def run(
        self,
        target: str,
        disease: Optional[str] = None,
        topic: Optional[str] = None,
        retmax: int = 25,
        recent_years_first: bool = True,
        year_from: Optional[int] = None,
        # ✅ 스키마에 맞추려면 query_id는 외부(UserQuery.query_id)에서 주입 가능해야 함
        query_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # ✅ query_id는 가능하면 외부에서 받은 값을 사용 (UserQuery.query_id와 연결)
        query_id = query_id or self._make_query_id()

        query = self.build_query(target, disease, topic)

        pmids: List[str] = []

        # ✅ hard-coded "2026" 제거: 현재 연도 기반
        current_year = datetime.now().year
        maxdate = str(current_year)

        if year_from is not None:
            mindate = str(year_from)
            pmids = self.pubmed.search(query, retmax=retmax, mindate=mindate, maxdate=maxdate)
        else:
            if recent_years_first:
                # 최근 3년 정도 우선
                mindate = str(current_year - 2)
                pmids = self.pubmed.search(query, retmax=retmax, mindate=mindate, maxdate=maxdate)

            if len(pmids) < max(8, retmax // 3):
                mindate = str(current_year - 7)  # 부족하면 8년 정도로 확장
                more = self.pubmed.search(query, retmax=retmax, mindate=mindate, maxdate=maxdate)
                seen = set(pmids)
                for x in more:
                    if x not in seen:
                        pmids.append(x)
                        seen.add(x)

        raw_papers = self.pubmed.fetch_details(pmids)

        # ✅ team paper.py 스키마에 "있는 필드만" 넣기
        papers_for_schema: List[Dict[str, Any]] = []
        for p in raw_papers:
            papers_for_schema.append(
                {
                    "pmid": str(p.pmid or ""),
                    "title": str(p.title or ""),
                    "year": self._year_to_int(p.year),
                    "journal": str(p.journal or ""),
                    "abstract_sentences": self._abstract_to_sentences(p.pmid, p.abstract),
                    "retrieval_reason": "keyword",  # keyword | synonym | update
                }
            )

        # ✅ 반환도 스키마에 있는 것만
        return {
            "query_id": query_id,
            "papers": papers_for_schema,
        }
