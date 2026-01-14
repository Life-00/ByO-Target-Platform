# Extractor 결과 저장

# Extractor에서 DB에 저장하려는 것 : knowledgeChunk
# KnowledgeChunk
# - 이미 LLM이 판단·구조화한 claim
# - target / disease / relation / confidence 포함
# - RAG에서 바로 reasoning에 쓰임

# services/chromadb/ingest_chunk.py

from app.schemas.knowledge import KnowledgeChunk
from app.core.chromadb import knowledge_collection


def _add_if_not_none(meta: dict, key: str, value):
    if value is not None:
        meta[key] = value

def add_chunks_to_chromadb(chunks: list[KnowledgeChunk]) -> None:
    """
    Store Extractor-produced KnowledgeChunks into ChromaDB.

    NOTE:
    - ChromaDB metadata must be flat (no dict / list)
    - Nested fields (stance, effect) are flattened
    """

    if not chunks:
        return

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(chunk.chunk_id)
        documents.append(chunk.claim)

        meta = {}

        # ---- identifiers ----
        _add_if_not_none(meta, "pmid", chunk.pmid)
        _add_if_not_none(meta, "query_id", chunk.query_id)

        # ---- bibliographic ----
        _add_if_not_none(meta, "paper_title", chunk.metadata.get("paper_title"))
        _add_if_not_none(meta, "journal", chunk.metadata.get("journal"))
        _add_if_not_none(meta, "year", chunk.metadata.get("year"))

        # ---- core entities ----
        _add_if_not_none(meta, "target", chunk.target)
        _add_if_not_none(meta, "disease", chunk.disease)

        # ---- evidence ----
        _add_if_not_none(meta, "evidence_level", chunk.evidence_level)
        _add_if_not_none(meta, "confidence", chunk.confidence)
        _add_if_not_none(meta, "chunk_type", chunk.chunk_type)

        # ---- flatten stance ----
        if chunk.stance:
            _add_if_not_none(meta, "stance_polarity", chunk.stance.get("polarity"))
            _add_if_not_none(meta, "stance_strength", chunk.stance.get("strength"))
            _add_if_not_none(meta, "stance_conditions", chunk.stance.get("conditions"))

        # ---- flatten effect ----
        if chunk.effect:
            _add_if_not_none(meta, "effect_direction", chunk.effect.get("direction"))
            _add_if_not_none(meta, "effect_target_outcome", chunk.effect.get("target_outcome"))
            _add_if_not_none(meta, "effect_confidence", chunk.effect.get("confidence"))

        # ---- flatten salience ----
        salience = chunk.metadata.get("salience")
        if salience:
            _add_if_not_none(meta, "salience_level", salience.get("level"))
            _add_if_not_none(meta, "salience_reason", salience.get("reason"))

        metadatas.append(meta)

    # upsert-like behavior
    try:
        knowledge_collection.delete(ids=ids)
    except Exception:
        pass

    knowledge_collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )