import os
import time
import chromadb

from langchain_upstage import UpstageDocumentParseLoader, UpstageEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata

from app.core.config import settings


class RAGService:
    def __init__(self):
        self.api_key = settings.UPSTAGE_API_KEY

        self.embeddings = UpstageEmbeddings(
            api_key=self.api_key,
            model=settings.UPSTAGE_EMBED_MODEL if hasattr(settings, "UPSTAGE_EMBED_MODEL") else "solar-embedding-1-large",
        )

        print(f"[{time.strftime('%H:%M:%S')}] [RAG] Connect {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
        self.client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)

        # 기본은 기존과 동일. 세션별 컬렉션으로 바꾸고 싶으면 get_vector_db()에서 처리
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
        session_id: str,
        email: str,
        file_id: str,
        collection_name: str | None = None,
        upsert: bool = False,
    ) -> dict:
        """
        file_id 기반으로 고유 ids를 생성해서 충돌을 막는다.
        upsert=False이면 이미 존재하는 ids는 건너뛰는 방향(벡터DB 특성상 add가 에러/무시될 수 있음).
        """
        vector_db = self.get_vector_db(collection_name)

        try:
            loader = UpstageDocumentParseLoader(file_path=file_path, api_key=self.api_key)
            raw_docs = loader.load()
            split_docs = self.text_splitter.split_documents(raw_docs)

            # ✅ 고유 ID: session + file_id + chunk_index
            ids = [f"{session_id}_{file_id}_{i}" for i in range(len(split_docs))]

            for doc in split_docs:
                doc.metadata["user_email"] = email
                doc.metadata["session_id"] = str(session_id)
                doc.metadata["file_id"] = str(file_id)
                doc.metadata["source"] = os.path.basename(file_path)

            final_docs = filter_complex_metadata(split_docs)

            if not upsert:
                # 이미 존재하는 id는 제외하고 add (충돌/중복 방지)
                # Chroma get으로 존재여부 확인 (ids 리스트로 조회)
                try:
                    existing = vector_db._collection.get(ids=ids)  # 내부 API지만 실용적
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

    def get_relevant_context(self, query: str, session_id: str, email: str, collection_name: str | None = None) -> str:
        """
        유사도 검색 시 텍스트 + 파일명 + 페이지를 묶어 반환
        """
        print(f"[{time.strftime('%H:%M:%S')}] [RAG] Retrieve (session={session_id})")

        vector_db = self.get_vector_db(collection_name)

        try:
            search_kwargs = {
                "filter": {"$and": [{"user_email": email}, {"session_id": str(session_id)}]},
                "k": 4,
            }

            docs = vector_db.similarity_search(query, **search_kwargs)
            if not docs:
                return "관련된 문서 내용을 찾을 수 없습니다."

            parts = []
            for i, doc in enumerate(docs):
                source_file = doc.metadata.get("source", "알 수 없는 파일")
                page_num = doc.metadata.get("page", "-")
                parts.append(
                    f"[근거 {i+1}]\n"
                    f"출처: {source_file} ({page_num}페이지)\n"
                    f"내용: {doc.page_content}\n"
                )
            return "\n".join(parts)

        except Exception as e:
            return f"문서 검색 중 오류가 발생했습니다: {str(e)}"


rag_service = RAGService()
