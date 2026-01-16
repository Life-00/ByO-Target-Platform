# app/agents/retriever/biorxiv_fetcher.py
from __future__ import annotations

import os
import time
import requests
from typing import Optional
from pathlib import Path


class BiorxivFetcher:
    """
    bioRxiv는 키워드 검색 API가 사실상 없고(주로 DOI/기간 기반),
    Europe PMC에서 preprint를 찾은 다음 DOI로 PDF 경로를 구성/다운로드하는 방식이 현실적.

    - bioRxiv는 PDF를 제공한다는 점은 공식 FAQ/소개에서 확인 가능.
    """
    def __init__(self, download_dir: str):
        p = Path(download_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        self.download_dir = str(p)

    @staticmethod
    def build_pdf_url_from_doi(doi: str) -> str:
        # bioRxiv 일반적인 패턴: https://www.biorxiv.org/content/<doi>.full.pdf
        # (doi에 버전(v1 등)이 포함될 수도 있음)
        doi = (doi or "").strip()
        return f"https://www.biorxiv.org/content/{doi}.full.pdf"

    def download_pdf(self, doi: str, file_stem: str) -> Optional[str]:
        pdf_url = self.build_pdf_url_from_doi(doi)
        if not doi or not pdf_url:
            return None

        # 파일명 안전화
        safe = "".join([c if c.isalnum() or c in {"-", "_"} else "_" for c in file_stem])[:120]
        save_path = os.path.join(self.download_dir, f"{safe}.pdf")

        try:
            print(f"[{time.strftime('%H:%M:%S')}] [bioRxiv] download: {pdf_url}")
            r = requests.get(pdf_url, timeout=25)
            if r.status_code != 200 or not r.content:
                print(f"[bioRxiv] download failed: {r.status_code}")
                return None

            with open(save_path, "wb") as f:
                f.write(r.content)

            return save_path
        except Exception as e:
            print(f"[bioRxiv] download error: {e}")
            return None
