import os
import time
from typing import List
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
            model="solar-embedding-1-large"
        )
        self.persist_directory = "./chroma_db"
        
        self.vector_db = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
            collection_name="byo_target_docs"
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        print(f"[{time.strftime('%H:%M:%S')}] [RAG-SERVICE] Initialized.")

    async def process_and_store(self, file_path: str, session_id: str, email: str):
        try:
            loader = UpstageDocumentParseLoader(file_path=file_path, api_key=self.api_key)
            raw_docs = loader.load()
            split_docs = self.text_splitter.split_documents(raw_docs)

            # 고유 ID 생성 (세션ID + 순번)
            ids = [f"{session_id}_{i}" for i in range(len(split_docs))]
            
            for doc in split_docs:
                doc.metadata["user_email"] = email
                doc.metadata["session_id"] = str(session_id)
                doc.metadata["source"] = os.path.basename(file_path)

            final_docs = filter_complex_metadata(split_docs)

            # ids를 명시적으로 전달하여 중복 충돌 방지
            self.vector_db.add_documents(final_docs, ids=ids) 
            print(f"[{time.strftime('%H:%M:%S')}] [RAG-STORE] Success with Unique IDs.")
            return True
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] [RAG-ERROR] {str(e)}")
            return False

    def get_relevant_context(self, query: str, session_id: str, email: str) -> str:
        """현재 유저의 세션 데이터만 필터링하여 검색"""
        print(f"[{time.strftime('%H:%M:%S')}] [RAG-RETRIEVE] Querying for session: {session_id}")
        
        try:
            search_kwargs = {
                "filter": {
                    "$and": [
                        {"user_email": email},
                        {"session_id": str(session_id)}
                    ]
                },
                "k": 5
            }
            
            docs = self.vector_db.similarity_search(query, **search_kwargs)
            context = "\n\n".join([doc.page_content for doc in docs])
            return context
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] [RAG-RETRIEVE-ERROR] {str(e)}")
            return ""

rag_service = RAGService()