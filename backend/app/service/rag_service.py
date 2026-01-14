# app/service/rag_service.py

import os
import time
import chromadb
from uuid import UUID

from langchain_upstage import UpstageDocumentParseLoader, UpstageEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_core.documents import Document

from app.core.config import settings
from typing import List, Optional


class RAGService:
    def __init__(self):
        self.api_key = settings.UPSTAGE_API_KEY

        self.embeddings = UpstageEmbeddings(
            api_key=self.api_key,
            model=settings.UPSTAGE_EMBED_MODEL if hasattr(settings, "UPSTAGE_EMBED_MODEL") else "solar-embedding-1-large",
        )

        print(f"[{time.strftime('%H:%M:%S')}] [RAG] Connect {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        self.client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        
        self.default_collection_name = "byo_target_docs"
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        print(f"[{time.strftime('%H:%M:%S')}] [RAG] Ready")

    def get_vector_db(self, collection_name: str | None = None) -> Chroma:
        return Chroma(
            client=self.client,
            collection_name=collection_name or self.default_collection_name,
            embedding_function=self.embeddings,
        )

    async def process_and_store(
        self,
        file_path: str,
        session_id: UUID,
        email: str,
        file_id: UUID,
        collection_name: str | None = None,
        upsert: bool = False,
    ) -> dict:
        vector_db = self.get_vector_db(collection_name)

        try:
            loader = UpstageDocumentParseLoader(file_path=file_path, api_key=self.api_key)
            raw_docs = loader.load()
            split_docs = self.text_splitter.split_documents(raw_docs)

            ids = [f"{session_id}_{file_id}_{i}" for i in range(len(split_docs))]

            for doc in split_docs:
                doc.metadata["user_email"] = email
                doc.metadata["session_id"] = str(session_id)
                doc.metadata["file_id"] = str(file_id)
                doc.metadata["source"] = os.path.basename(file_path)
                doc.metadata["type"] = "raw_text"

            final_docs = filter_complex_metadata(split_docs)

            if not upsert:
                try:
                    existing = vector_db._collection.get(ids=ids)
                    existing_ids = set(existing.get("ids", []) or [])
                except Exception:
                    existing_ids = set()

                if existing_ids:
                    filtered = [(d, i) for d, i in zip(final_docs, ids) if i not in existing_ids]
                    final_docs = [d for d, _ in filtered]
                    ids = [i for _, i in filtered]

            if not final_docs:
                return {"ok": True, "chunk_count": 0, "skipped_all": True}

            vector_db.add_documents(final_docs, ids=ids)
            return {"ok": True, "chunk_count": len(final_docs), "skipped_all": False}

        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_relevant_context(
        self, 
        query: str, 
        session_id: UUID, 
        email: str, 
        file_ids: Optional[List[UUID]] = None,
        collection_name: str | None = None
    ) -> str:
        """
        RAG 검색 수행 및 메타데이터(페이지 번호) 포함 포맷팅
        """
        print(f"[{time.strftime('%H:%M:%S')}] [RAG] Retrieve (session={session_id}, files={len(file_ids) if file_ids else 'ALL'})")

        vector_db = self.get_vector_db(collection_name)

        try:
            base_conditions = [
                {"user_email": email},
                {"session_id": str(session_id)}
            ]

            if file_ids:
                str_ids = [str(fid) for fid in file_ids]
                file_condition = {
                    "$or": [
                        {"file_id": {"$in": str_ids}}, 
                        {"pmid": {"$in": str_ids}}     
                    ]
                }
                base_conditions.append(file_condition)

            final_filter = {"$and": base_conditions}

            generic_keywords = ["요약", "정리", "읽어", "뭐야", "분석", "summary", "explain", "analyze", "read", "content"]
            is_generic_query = any(k in query.lower() for k in generic_keywords)

            docs = []
            
            # 요약 모드 처리 (생략 없이 유지)
            if is_generic_query and file_ids:
                target_ids = []
                for fid in file_ids:
                    target_ids.append(f"{session_id}_{fid}_0")
                    target_ids.append(f"{session_id}_{fid}_auto_0")
                    target_ids.append(f"{session_id}_{fid}_auto_1")
                
                try:
                    results = vector_db._collection.get(ids=target_ids)
                    if results and results['documents']:
                        for i, content in enumerate(results['documents']):
                            if content:
                                meta = results['metadatas'][i] if results['metadatas'] else {}
                                docs.append(Document(page_content=content, metadata=meta))
                except Exception: pass
            
            if not docs:
                search_kwargs = {"filter": final_filter, "k": 5}
                docs = vector_db.similarity_search(query, **search_kwargs)
            
            if not docs:
                if file_ids:
                    return "선택하신 파일에 대한 분석 정보를 찾을 수 없습니다."
                else:
                    return "관련된 문서 내용을 찾을 수 없습니다."

            # 🔥 [핵심 변경] 페이지 번호와 출처를 포함하여 텍스트 포맷팅
            parts = []
            for i, doc in enumerate(docs):
                source_file = doc.metadata.get("source") or doc.metadata.get("paper_title") or "Unknown File"
                
                # Upstage Loader는 보통 'page' 키에 1-based 또는 0-based 페이지 정보를 담음
                # 메타데이터에서 안전하게 가져옴 (없으면 'Unknown')
                page_num = doc.metadata.get("page", None)
                
                # 페이지 정보 문자열 생성
                if page_num is not None:
                    # 0부터 시작하는 경우 +1, 아니면 그대로 사용
                    page_str = f"Page {int(page_num) + 1}"
                else:
                    page_str = "Page Unknown"

                parts.append(
                    f"[[{source_file} | {page_str}]]\n"  # LLM이 인용할 마커
                    f"{doc.page_content}\n"
                )
            return "\n\n".join(parts)

        except Exception as e:
            print(f"[RAG Error] {str(e)}")
            return ""
        
    async def get_full_document_text(self, session_id: UUID, file_id: UUID) -> str:
        vector_db = self.get_vector_db()
        try:
            collection = vector_db._collection
            results = collection.get(
                where={
                    "$and": [
                        {"session_id": str(session_id)},
                        {"file_id": str(file_id)}
                    ]
                }
            )
            
            if not results or not results['ids']: return ""

            combined = zip(results['ids'], results['documents'])
            sorted_docs = sorted(combined, key=lambda x: int(x[0].split('_')[-1]))
            
            full_text = "\n\n".join([doc for _, doc in sorted_docs])
            return full_text

        except Exception as e:
            print(f"[RAG Summary Error] {e}")
            return ""

rag_service = RAGService()