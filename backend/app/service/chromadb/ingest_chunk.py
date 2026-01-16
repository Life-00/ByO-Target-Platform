# app/service/chromadb/ingest_chunk.py

from typing import List
from langchain_core.documents import Document
from app.schemas.knowledge import KnowledgeChunk
from app.service.rag_service import rag_service  # ✅ RAG 서비스 연동

def _add_if_not_none(meta: dict, key: str, value):
    if value is not None:
        meta[key] = value

def add_chunks_to_chromadb(chunks: List[KnowledgeChunk], collection_name: str = "extracted_knowledge") -> None:
    """
    Store Extractor-produced KnowledgeChunks into ChromaDB via RAGService.
    """

    if not chunks:
        return
    
    # ✅ rag_service를 통해 LangChain VectorStore 객체 획득
    # (이미 Upstage Embedding 설정이 되어 있어 자동으로 임베딩됨)
    vector_db = rag_service.get_vector_db(collection_name)

    docs_to_add = []
    ids_to_add = []

    for chunk in chunks:
        # 1. 메타데이터 구성 (작성하신 Flattening 로직 그대로 유지 - 아주 좋습니다 👍)
        meta = {}

        # ---- identifiers ----
        _add_if_not_none(meta, "pmid", chunk.pmid)
        _add_if_not_none(meta, "query_id", chunk.query_id)

        # ---- bibliographic ----
        if chunk.metadata:
            _add_if_not_none(meta, "paper_title", chunk.metadata.get("paper_title"))
            _add_if_not_none(meta, "journal", chunk.metadata.get("journal"))
            _add_if_not_none(meta, "year", chunk.metadata.get("year"))
            
            # salience handling
            salience = chunk.metadata.get("salience")
            if salience:
                # dict인 경우와 객체인 경우 모두 방어
                if isinstance(salience, dict):
                    _add_if_not_none(meta, "salience_level", salience.get("level"))
                    _add_if_not_none(meta, "salience_reason", salience.get("reason"))
                elif hasattr(salience, "level"): # Pydantic model
                    _add_if_not_none(meta, "salience_level", salience.level)
                    _add_if_not_none(meta, "salience_reason", salience.reason)

        # ---- core entities ----
        _add_if_not_none(meta, "target", chunk.target)
        _add_if_not_none(meta, "disease", chunk.disease)

        # ---- evidence ----
        _add_if_not_none(meta, "evidence_level", chunk.evidence_level)
        _add_if_not_none(meta, "confidence", chunk.confidence)
        _add_if_not_none(meta, "chunk_type", chunk.chunk_type)

        # ---- flatten stance ----
        if chunk.stance:
            # dict로 변환되어 들어온다고 가정 (Agent에서 model_dump 함)
            stance = chunk.stance
            _add_if_not_none(meta, "stance_polarity", stance.get("polarity"))
            _add_if_not_none(meta, "stance_strength", stance.get("strength"))
            _add_if_not_none(meta, "stance_conditions", stance.get("conditions"))

        # ---- flatten effect ----
        if chunk.effect:
            effect = chunk.effect
            _add_if_not_none(meta, "effect_direction", effect.get("direction"))
            _add_if_not_none(meta, "effect_target_outcome", effect.get("target_outcome"))
            _add_if_not_none(meta, "effect_confidence", effect.get("confidence"))

        # 2. Document 객체 생성 (LangChain 호환)
        doc = Document(
            page_content=chunk.claim, # 임베딩 대상 텍스트
            metadata=meta
        )
        
        docs_to_add.append(doc)
        ids_to_add.append(chunk.chunk_id)

    # 3. Upsert 구현 (삭제 후 추가)
    # LangChain ChromaWrapper는 upsert를 직접 지원하지 않으므로, 기존 ID가 있다면 지우는 것이 안전함
    try:
        # _collection에 접근하여 raw client 기능 사용
        vector_db._collection.delete(ids=ids_to_add)
    except Exception:
        pass # 없으면 패스

    # 4. 저장 (자동 임베딩 수행됨)
    vector_db.add_documents(documents=docs_to_add, ids=ids_to_add)
    print(f"[ChromaDB] Ingested {len(docs_to_add)} chunks into '{collection_name}'")