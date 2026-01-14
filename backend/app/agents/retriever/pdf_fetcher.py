# app/agents/retriever/pdf_fetcher.py
import os
import time
import requests
from typing import Optional
from app.core.config import settings

class PDFFetcher:
    def __init__(self, download_dir: str = "data/uploads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
        self.email = settings.NCBI_EMAIL
        self.tool = settings.NCBI_TOOL
        
        self.headers = {
            "User-Agent": f"{self.tool}/1.0 ({self.email})"
        }

    def _pmid_to_pmcid(self, pmid: str) -> Optional[str]:
        """PMID -> PMCID 변환 (NCBI Converter API)"""
        url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
        params = {
            "ids": pmid,
            "format": "json",
            "tool": self.tool,
            "email": self.email
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "records" in data and len(data["records"]) > 0:
                    record = data["records"][0]
                    return record.get("pmcid")
        except Exception as e:
            print(f"[PDFFetcher] ID Conv Error: {e}")
        return None

    def download_pdf(self, pmid: str) -> Optional[str]:
        """Open Access 논문 PDF 다운로드"""
        filename = f"{pmid}.pdf"
        save_path = os.path.join(self.download_dir, filename)
        
        if os.path.exists(save_path):
            return save_path

        pmcid = self._pmid_to_pmcid(pmid)
        if not pmcid:
            return None

        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
        
        try:
            time.sleep(0.5) # 서버 부하 방지
            resp = requests.get(pdf_url, headers=self.headers, stream=True, timeout=15)
            
            content_type = resp.headers.get("Content-Type", "")
            if resp.status_code == 200 and "application/pdf" in content_type:
                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
                return save_path
        except Exception as e:
            print(f"[PDFFetcher] Download Error ({pmid}): {e}")
        
        return None