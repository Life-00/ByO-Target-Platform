import chromadb
from app.core.config import settings
from app.core.embeddings import UpstageChromaEmbedding

chroma_client = chromadb.PersistentClient(
    path=settings.CHROMA_PERSIST_DIR  # config에서 주입
)

knowledge_collection = chroma_client.get_or_create_collection(
    name="knowledge_chunks",
    embedding_function=UpstageChromaEmbedding()
)