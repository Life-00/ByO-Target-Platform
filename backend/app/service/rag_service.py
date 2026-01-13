import os
import time
import chromadb
from uuid import UUID

from langchain_upstage import UpstageDocumentParseLoader, UpstageEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata

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
        """
        파일을 벡터화하여 ChromaDB에 저장
        """
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

    # ✅ async 필수 적용 완료
    async def get_relevant_context(
        self, 
        query: str, 
        session_id: UUID, 
        email: str, 
        file_ids: Optional[List[UUID]] = None,
        collection_name: str | None = None
    ) -> str:
        """
        RAG 검색 수행. file_ids가 있으면 해당 파일 내에서만 검색.
        """
        print(f"[{time.strftime('%H:%M:%S')}] [RAG] Retrieve (session={session_id}, files={len(file_ids) if file_ids else 'ALL'})")

        vector_db = self.get_vector_db(collection_name)

        try:
            # 1. 기본 필터
            filter_conditions = [
                {"user_email": email},
                {"session_id": str(session_id)}
            ]

            # 2. 파일 선택 필터
            if file_ids:
                filter_conditions.append({"file_id": {"$in": [str(fid) for fid in file_ids]}})

            # 요약 모드 키워드
            generic_keywords = ["요약", "정리", "읽어", "뭐야", "분석", "summary", "explain", "analyze", "read"]
            is_generic_query = any(k in query.lower() for k in generic_keywords)

            docs = []
            
            # 3-A. 요약 모드 (파일 앞부분 조회)
            if is_generic_query and file_ids:
                print(f"[{time.strftime('%H:%M:%S')}] [RAG] Generic query detected -> Fetching first chunks")
                target_ids = []
                for fid in file_ids:
                    target_ids.append(f"{session_id}_{fid}_0")
                    target_ids.append(f"{session_id}_{fid}_1")
                
                results = vector_db._collection.get(ids=target_ids)
                
                if results and results['documents']:
                    for i, content in enumerate(results['documents']):
                        meta = results['metadatas'][i] if results['metadatas'] else {}
                        from langchain_core.documents import Document
                        docs.append(Document(page_content=content, metadata=meta))
            
            # 3-B. 일반 검색 (Similarity Search)
            if not docs:
                search_kwargs = {
                    "filter": {"$and": filter_conditions},
                    "k": 4, 
                }
                docs = vector_db.similarity_search(query, **search_kwargs)
            
            # ✅ [수정] 검색 결과 없음 + 파일 선택됨 = Extractor 미실행 가능성 높음
            if not docs:
                if file_ids:
                    return (
                        "선택하신 파일에서 내용을 찾을 수 없습니다. "
                        "해당 파일이 'Extractor' 에이전트를 통해 분석(Indexing)되었는지 확인해 주세요. "
                        "아직 분석되지 않았다면 Extractor 탭에서 실행 버튼을 눌러주세요."
                    )
                else:
                    return "관련된 문서 내용을 찾을 수 없습니다."

            parts = []
            for i, doc in enumerate(docs):
                source_file = doc.metadata.get("source", "알 수 없는 파일")
                page_num = doc.metadata.get("page", "-")
                parts.append(
                    f"[참고 문헌 {i+1}]\n"
                    f"파일명: {source_file}\n"
                    f"내용: {doc.page_content[:1000]}...\n"
                )
            return "\n".join(parts)

        except Exception as e:
            print(f"[RAG Error] {str(e)}")
            return ""


rag_service = RAGService()