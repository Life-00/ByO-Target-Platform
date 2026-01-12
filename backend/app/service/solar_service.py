import time
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.service.rag_service import rag_service

class SolarService:
    def __init__(self):
        # LangChain의 ChatUpstage 인터페이스를 사용하여 Solar-Pro 모델 로드
        self.llm = ChatUpstage(
            api_key=settings.UPSTAGE_API_KEY,
            model=settings.UPSTAGE_MODEL # solar-pro
        )
        print(f"[{time.strftime('%H:%M:%S')}] [SOLAR-SERVICE] Service Initialized with LangChain.")

    async def get_chat_response(self, user_email: str, message: str, session_id: str = None):
        """
        RAG 컨텍스트를 포함하여 Solar-Pro 모델로부터 답변을 생성합니다.
        """
        print(f"\n[{time.strftime('%H:%M:%S')}] [SOLAR-LLM] Reasoning for user: {user_email} | Session: {session_id}")
        
        start_time = time.time()
        
        # 1. RAG 컨텍스트 확보 (세션 ID가 있을 경우에만 실행)
        context = ""
        if session_id:
            try:
                # rag_service를 통해 유저 및 세션별로 필터링된 관련 문서 조각들을 가져옴
                context = rag_service.get_relevant_context(message, session_id, user_email)
            except Exception as e:
                print(f"  - [RAG-WARN] Context retrieval failed: {str(e)}")

        # 2. 시스템 프롬프트 구성 (Context 유무에 따라 동적 변경)
        system_instruction = "너는 전문적인 바이오 타겟 검증 어시스턴트이다. 연구원의 질문에 대해 과학적 근거를 바탕으로 친절하게 답변하라."
        
        if context:
            system_instruction += f"\n\n[참고 문서 내용]\n{context}\n\n위의 [참고 문서 내용]에 사용자의 질문과 관련된 정보가 있다면 이를 우선적으로 활용하여 답변하라."

        # 3. 메시지 리스트 생성
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=message)
        ]

        try:
            # 4. 모델 호출 (invoke)
            response = self.llm.invoke(messages)
            
            end_time = time.time()
            latency = end_time - start_time
            
            print(f"  - Result: Success | Latency: {latency:.2f}s")
            return response.content

        except Exception as e:
            print(f"  - [SOLAR-ERROR] Critical Error during LLM reasoning: {str(e)}")
            return "죄송합니다. 분석 중 오류가 발생했습니다."

solar_service = SolarService()