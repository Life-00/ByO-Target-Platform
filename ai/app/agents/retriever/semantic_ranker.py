# app/agents/retriever/semantic_ranker.py
from __future__ import annotations

from typing import Dict, List, Tuple
import math

from app.core.embeddings import UpstageChromaEmbedding
from app.schemas.retrieval import Paper


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb + 1e-12)


class SemanticRanker:
    def __init__(self):
        self.emb = UpstageChromaEmbedding()

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
        top_idx = [idx for idx, _ in scored[: min(top_n, len(scored))]]

        # ✅ 점수 순서대로 반환
        top_papers = [papers[i] for i in top_idx]
        return top_papers, scores
