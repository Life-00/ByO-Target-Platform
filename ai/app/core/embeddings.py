# app/core/embeddings.py
import os
from langchain_upstage import UpstageEmbeddings

class UpstageChromaEmbedding:
    def __init__(self):
        api_key = os.getenv("UPSTAGE_API_KEY")
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY not set")

        self._emb = UpstageEmbeddings(
            api_key=api_key,
            model="solar-embedding-1-large"
        )

    # ❗️ 파라미터 이름 반드시 input
    def __call__(self, input):
        # input: List[str]
        return self._emb.embed_documents(input)

    def embed_query(self, query: str):
        return self._emb.embed_query(query)

    def name(self):
        return "upstage-solar-embedding"
