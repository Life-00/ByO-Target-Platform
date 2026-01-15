# app/agents/retriever/arxiv_fetcher.py
import os
import time
import requests
import xml.etree.ElementTree as ET
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from app.schemas.retrieval import Paper, AbstractSentence
from app.core.config import get_uploads_dir


class ArxivFetcher:
    def __init__(self, download_dir: str | None = None):
        """
        arXiv 전용 페처를 초기화합니다.
        - download_dir가 None이면 get_uploads_dir()로 통일
        - 상대경로가 들어와도 절대경로로 보정해서 저장 (CWD 의존 제거)
        """
        if not download_dir:
            p = get_uploads_dir()
        else:
            pp = Path(download_dir)
            # 상대경로면 프로젝트 루트 기준으로 보정
            p = (get_uploads_dir().parent / pp).resolve() if not pp.is_absolute() else pp.resolve()
            p.mkdir(parents=True, exist_ok=True)

        self.download_dir = str(p)
        self.base_url = "http://export.arxiv.org/api/query?"
        print(f"[arXiv-Fetch] download_dir={self.download_dir}")

    def search_and_download(self, query: str, max_results: int = 5, query_id: str = "arxiv_default") -> List[Paper]:
        """
        arXiv API를 통해 검색하고, 상세 정보(저자, 연도) 파싱 및 PDF를 확보합니다.
        Pydantic 유효성 에러 방지를 위해 retrieval_reason과 query_id를 포함합니다.
        """
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        papers: List[Paper] = []
        try:
            print(f"\n[arXiv-Fetch] 🔍 검색어: '{query}' (대상: {max_results}건)")
            resp = requests.get(self.base_url, params=params, timeout=20)

            if resp.status_code != 200:
                print(f"❌ [arXiv-Fetch] API 연결 실패: {resp.status_code}")
                return []

            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "arxiv": "http://arxiv.org/schemas/atom",
            }

            root = ET.fromstring(resp.text)
            entries = root.findall("atom:entry", ns)

            total_found = len(entries)
            print(f"[arXiv-Fetch] 총 {total_found}개의 논문 엔트리를 발견했습니다.")

            for idx, entry in enumerate(entries):
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
                arxiv_full_id = entry.find("atom:id", ns).text
                arxiv_id = arxiv_full_id.split("/")[-1]

                authors_list = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

                pub_date_str = entry.find("atom:published", ns).text
                try:
                    year = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%SZ").year
                except Exception:
                    year = datetime.now().year

                # PDF 링크 찾기
                pdf_url = ""
                for link in entry.findall("atom:link", ns):
                    if link.attrib.get("title") == "pdf":
                        pdf_url = link.attrib.get("href")

                print(f"[arXiv-Fetch] [{idx+1}/{total_found}] 처리 중: {title[:45]}...")

                pdf_path = self.download_pdf(pdf_url, arxiv_id)

                sentences = [s.strip() for s in summary.split(".") if len(s.strip()) > 10]
                abs_sentences = [AbstractSentence(sentence_id=f"arxiv_{arxiv_id}_{i}", text=s) for i, s in enumerate(sentences)]

                paper = Paper(
                    pmid=arxiv_id,
                    title=title,
                    authors=authors_list,
                    year=year,
                    journal="arXiv",
                    abstract_sentences=abs_sentences,
                    pdf_storage_path=pdf_path,
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    source="arxiv",
                    retrieval_reason="arxiv_search",
                    query_id=query_id,
                )
                papers.append(paper)

            print(f"[arXiv-Fetch] 검색 및 객체화 완료: {len(papers)}건")

        except Exception as e:
            print(f"❌ [arXiv-Fetch] 전체 프로세스 중 치명적 에러: {e}")

        return papers

    def download_pdf(self, pdf_url: str, arxiv_id: str) -> Optional[str]:
        """arXiv에서 실물 PDF를 다운로드하여 저장합니다."""
        if not pdf_url:
            print(f"   ⚠️ [arXiv] PDF 링크가 존재하지 않음 (ID: {arxiv_id})")
            return None

        save_path = os.path.join(self.download_dir, f"{arxiv_id}.pdf")

        if os.path.exists(save_path):
            print(f"   ✅ [arXiv] 이미 로컬에 적재됨: {save_path}")
            return save_path

        try:
            print(f"   📥 [arXiv] 실물 PDF 적재 시작: {pdf_url}")
            time.sleep(1.0)

            resp = requests.get(pdf_url, timeout=30)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                print(f"   ✅ [arXiv] 파일 저장 성공: {save_path}")
                return save_path

            print(f"   ❌ [arXiv] 다운로드 응답 실패: {resp.status_code}")

        except Exception as e:
            print(f"   ⚠️ [arXiv] 다운로드 네트워크 에러: {e}")

        return None
