# app/agents/retriever/semantic_ranker.py
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import math

from app.core.embeddings import UpstageChromaEmbedding
from app.schemas.retrieval import Paper


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-12)


class SemanticRanker:
    def __init__(
        self,
            use_knee_cutoff: bool = True,
            knee_min_k: int = 5,
            knee_max_k: Optional[int] = None,
        ):
            self.emb = UpstageChromaEmbedding()
            self.use_knee_cutoff = use_knee_cutoff
            self.knee_min_k = knee_min_k
            self.knee_max_k = knee_max_k

    def _knee_cutoff(self, sorted_scores: List[float], max_k: int) -> int:
        """
        Kneedle 스타일: 정규화된 점수-위치 곡선에서 (y - x)가 최대인 지점을 택해 컷오프.
        sorted_scores: 내림차순.
        """
        n = len(sorted_scores)
        if n == 0:
            return 0
        if n == 1:
            return 1

        max_k = max(1, min(max_k, n))
        smax, smin = sorted_scores[0], sorted_scores[-1]
        denom = smax - smin

        best_idx, best_gap = 0, float("-inf")
        for i, s in enumerate(sorted_scores):
            y = (s - smin) / denom if denom > 1e-8 else 1.0
            x = i / (n - 1)
            gap = y - x
            if gap > best_gap:
                best_gap = gap
                best_idx = i

            k = best_idx + 1  # include knee item
            k = max(self.knee_min_k, min(k, max_k))
        return k

    def rank(self, query_text: str, papers: List[Paper], top_n: int = 200) -> Tuple[List[Paper], Dict[str, float]]:
        if not papers:
            return [], {}

        qv = self.emb.embed_query(query_text)

        doc_texts: List[str] = []
        for p in papers:
            abs_text = " ".join([s.text for s in p.abstract_sentences])
            doc_texts.append(f"{p.title}\n{abs_text}")

        dvs = self.emb(doc_texts)

        scores: Dict[str, float] = {}
        scored: List[Tuple[int, float]] = []  # (index, score)

        for idx, (p, dv) in enumerate(zip(papers, dvs)):
            s = _cosine(qv, dv)
            scores[p.pmid] = s
            scored.append((idx, s))

        scored.sort(key=lambda x: x[1], reverse=True)

        if self.use_knee_cutoff:
            max_cap = min(top_n, len(scored))
            if self.knee_max_k is not None:
                max_cap = min(max_cap, self.knee_max_k)
            top_k = self._knee_cutoff([s for _, s in scored], max_cap)
        else:
            top_k = min(top_n, len(scored))

        top_idx = [idx for idx, _ in scored[:top_k]]
        top_papers = [papers[i] for i in top_idx]
        return top_papers, scores