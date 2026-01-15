from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.agents.retriever.types import ExpandedQuery
from app.schemas.retrieval import Paper


class LiteratureAdapter(ABC):
    source: str

    @abstractmethod
    def fetch(self, expanded_queries: List[ExpandedQuery], retmax: Optional[int] = None) -> List[Paper]:
        """Fetch papers for the expanded queries."""
        ...
