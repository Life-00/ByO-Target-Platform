from langchain_upstage import UpstageEmbeddings
from app.core.config import settings 

class UpstageChromaEmbedding:
    def __init__(self):
        api_key = settings.UPSTAGE_API_KEY
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY not set")

        self._emb = UpstageEmbeddings(
            api_key=api_key,
            model="solar-embedding-1-large"
        )

    def __call__(self, input):
        return self._emb.embed_documents(input)

    def embed_query(self, query: str):
        return self._emb.embed_query(query)

    def name(self):
        return "upstage-solar-embedding"