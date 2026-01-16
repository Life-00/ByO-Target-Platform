from __future__ import annotations

import time
from typing import Any, Dict, Optional
import requests


class BioRxivClient:
    """
    bioRxiv API client (DOI 기반 details)
    Docs: https://api.biorxiv.org/ ... /details/[server]/[DOI] :contentReference[oaicite:12]{index=12}
    """

    def __init__(self, base_url: str = "https://api.biorxiv.org"):
        self.base_url = base_url.rstrip("/")

    def details(self, doi: str, server: str = "biorxiv", timeout: float = 20.0, retries: int = 3) -> Dict[str, Any]:
        # API에서 DOI는 URL path라서 슬래시 포함 -> 그대로 두는 게 일반적
        url = f"{self.base_url}/details/{server}/{doi}"
        last_err: Optional[Exception] = None
        for i in range(retries):
            try:
                resp = requests.get(url, timeout=timeout)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                last_err = e
                time.sleep(0.4 * (2 ** i))
        assert last_err is not None
        raise last_err
