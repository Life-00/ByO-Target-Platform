import chromadb
from app.core.embeddings import UpstageChromaEmbedding

PERSIST_DIR = "/tmp/chroma_db"

chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)

papers_collection = chroma_client.get_or_create_collection(
    name="papers",
    embedding_function=UpstageChromaEmbedding()
)