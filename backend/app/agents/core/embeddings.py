# app/core/embeddings.py

import os
from langchain_upstage import UpstageEmbeddings


class UpstageChromaEmbedding:
    """
    ChromaDB-compatible embedding adapter.

    Rules:
    - __call__(input: List[str]) -> List[List[float]]
    - embed_query(input: str) -> List[List[float]]
    """

    def __init__(self):
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY not set")

        self._emb = UpstageEmbeddings(
            api_key=api_key,
            model="solar-embedding-1-large"
        )

    # For document embeddings
    def __call__(self, input):
        vectors = self._emb.embed_documents(input)

        if not isinstance(vectors, list) or not isinstance(vectors[0], list):
            raise TypeError(
                f"embed_documents must return List[List[float]], got {type(vectors)}"
            )

        return vectors

    # For query embeddings (IMPORTANT)
    def embed_query(self, input: str, **kwargs):
        vec = self._emb.embed_query(input)

        # Case 1: already List[float]
        if isinstance(vec, list) and len(vec) > 0 and isinstance(vec[0], float):
            return [vec]  # 🔑 반드시 이중 리스트

        # Case 2: List[List[float]]
        if isinstance(vec, list) and len(vec) > 0 and isinstance(vec[0], list):
            return vec

        raise TypeError(
            f"embed_query must return List[List[float]] or List[float], got {type(vec)}"
        )

    def name(self):
        return "upstage-solar-embedding"