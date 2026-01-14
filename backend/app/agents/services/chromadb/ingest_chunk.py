# Extractor 결과 저장

# Extractor에서 DB에 저장하려는 것 : knowledgeChunk
# KnowledgeChunk
# - 이미 LLM이 판단·구조화한 claim
# - target / disease / relation / confidence 포함
# - RAG에서 바로 reasoning에 쓰임

# services/chromadb/ingest_chunks.py

from app.schemas.knowledge import KnowledgeChunk
from app.core.chromadb import knowledge_collection

def add_chunks_to_chromadb(chunks: list[KnowledgeChunk]) -> None:
    """
    Store Extractor-produced KnowledgeChunks into vector DB.

    - One document per KnowledgeChunk (claim-level)
    - Used by Synthesizer for RAG
    """
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk.chunk_id)
        documents.append(chunk.claim)
        metadatas.append({
            "pmid": chunk.pmid, # PubMed ID
            "paper_title": chunk.metadata.get("paper_title"),  # 논문 제목
            "journal": chunk.metadata.get("journal"), # 투고된 학회명
            "year": chunk.metadata.get("year"), # 투고된 연도

            "query_id": chunk.query_id,
            "target": chunk.target,
            "disease": chunk.disease,
            "stance": chunk.stance,
            "effect": chunk.effect,
            "evidence_level": chunk.evidence_level,
            "confidence": chunk.confidence,
        })

    knowledge_collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )
