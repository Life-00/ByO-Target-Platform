# app/core/embeddings.py
from langchain_upstage import UpstageEmbeddings
from app.core.config import settings  

class UpstageChromaEmbedding:
    def __init__(self):
        # settings에서 API 키 가져오기
        api_key = settings.UPSTAGE_API_KEY
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY not set in settings")

        self._emb = UpstageEmbeddings(
            api_key=api_key,
            model="solar-embedding-1-large"
        )

    # ❗️ 파라미터 이름 반드시 input (ChromaDB 호환성)
    def __call__(self, input):
        # input: List[str]
        return self._emb.embed_documents(input)

    def embed_query(self, query: str):
        return self._emb.embed_query(query)

    def name(self):
        return "upstage-solar-embedding"