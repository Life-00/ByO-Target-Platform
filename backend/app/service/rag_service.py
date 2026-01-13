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
            model="solar-embedding-1-large"
        )
        
        print(f"[{time.strftime('%H:%M:%S')}] [RAG-INIT] Connecting to Vector DB at {settings.CHROMA_HOST}:{settings.CHROMA_PORT}...")
        
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        
        self.vector_db = Chroma(
            client=self.client,
            collection_name="byo_target_docs",
            embedding_function=self.embeddings
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        print(f"[{time.strftime('%H:%M:%S')}] [RAG-SERVICE] Server Connection Success.")

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
        """
        유사도 검색 시 텍스트와 함께 파일명, 페이지 정보를 묶어서 에이전트에게 전달합니다.
        """
        print(f"[{time.strftime('%H:%M:%S')}] [RAG-RETRIEVE] Searching for context (Session: {session_id})")
        
        try:
            # 현재 세션과 유저에 해당하는 데이터만 필터링
            search_kwargs = {
                "filter": {
                    "$and": [
                        {"user_email": email},
                        {"session_id": str(session_id)}
                    ]
                },
                "k": 4 
            }
            
            docs = self.vector_db.similarity_search(query, **search_kwargs)
            
            if not docs:
                return "관련된 문서 내용을 찾을 수 없습니다."

            context_parts = []
            for i, doc in enumerate(docs):
                # Upstage 파서가 제공하는 메타데이터 추출
                source_file = doc.metadata.get("source", "알 수 없는 파일")
                page_num = doc.metadata.get("page", "-")
                
                # 에이전트가 학습된 대로 근거를 인용할 수 있도록 포맷팅
                formatted_doc = (
                    f"[근거 {i+1}]\n"
                    f"출처: {source_file} ({page_num}페이지)\n"
                    f"내용: {doc.page_content}\n"
                )
                context_parts.append(formatted_doc)
                
            return "\n".join(context_parts)

        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] [RAG-ERROR] {str(e)}")
            return "문서 검색 중 오류가 발생했습니다."
        
    

rag_service = RAGService()