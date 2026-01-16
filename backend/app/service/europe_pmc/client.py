from __future__ import annotations

import time
from typing import Any, Dict, Optional
import requests


class EuropePMCClient:
    """
    Europe PMC REST API client
    - search endpoint 기반으로 metadata(abstract 포함)를 받아오는 용도
    Docs: Europe PMC RestfulWebService /search?query=...&format=json :contentReference[oaicite:9]{index=9}
    """

    def __init__(self, base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"):
        self.base_url = base_url.rstrip("/")

    def search(
        self,
        query: str,
        page_size: int = 25,
        result_type: str = "core",
        cursor_mark: str = "*",
        timeout: float = 20.0,
        retries: int = 3,
        base_sleep: float = 0.4,
    ) -> Dict[str, Any]:
        """
        Europe PMC search (JSON)
        - cursorMark 페이징을 기본으로 사용
        """
        url = f"{self.base_url}/search"
        params = {
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "resultType": result_type,
            "cursorMark": cursor_mark,
        }

        last_err: Optional[Exception] = None
        for i in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_err = e
                time.sleep(base_sleep * (2 ** i))

        assert last_err is not None
        raise last_err
