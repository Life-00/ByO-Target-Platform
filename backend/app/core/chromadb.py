# app/core/chromadb.py
import chromadb
from app.core.config import settings
from app.core.embeddings import UpstageChromaEmbedding

print(f"[ChromaDB] Connecting to {settings.CHROMA_HOST}:{settings.CHROMA_PORT}...")

# Docker/Server 환경에 맞게 HttpClient 사용
chroma_client = chromadb.HttpClient(
    host=settings.CHROMA_HOST,
    port=settings.CHROMA_PORT
)

# 논문 저장용 컬렉션 생성 (기존 RAG와 분리된 컬렉션 사용)
papers_collection = chroma_client.get_or_create_collection(
    name="papers",
    embedding_function=UpstageChromaEmbedding()
)