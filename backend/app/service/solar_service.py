import time
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage 
from app.core.config import settings
from app.service.rag_service import rag_service

class SolarService:
    def __init__(self):
        self.llm = ChatUpstage(
            api_key=settings.UPSTAGE_API_KEY,
            model=settings.UPSTAGE_MODEL
        )
        print(f"[{time.strftime('%H:%M:%S')}] [SOLAR-SERVICE] Service Initialized.")

    async def get_chat_response(self, user_email: str, message: str, session_id: str = None, history: list = None):
        """
        RAG 컨텍스트와 대화 히스토리를 포함하여 답변을 생성합니다.
        """
        print(f"\n[{time.strftime('%H:%M:%S')}] [SOLAR-LLM] Reasoning with History ({len(history) if history else 0} msgs)")
        
        start_time = time.time()
        
        # 1. RAG 컨텍스트 확보
        context = ""
        if session_id:
            try:
                context = rag_service.get_relevant_context(message, session_id, user_email)
            except Exception as e:
                print(f"  - [RAG-WARN] Context retrieval failed: {str(e)}")

        # 2. 시스템 프롬프트
        system_instruction = "너는 전문적인 바이오 타겟 검증 어시스턴트이다. 연구원의 질문에 대해 과학적 근거를 바탕으로 친절하게 답변하라."
        
        if context:
            system_instruction += f"\n\n[참고 문서 내용]\n{context}\n\n위의 [참고 문서 내용]에 사용자의 질문과 관련된 정보가 있다면 이를 우선적으로 활용하여 답변하라."

        # [수정] 메시지 체인 구성 (System + History)
        messages = [SystemMessage(content=system_instruction)]

        if history:
            for msg in history:
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'ai':
                    messages.append(AIMessage(content=msg['content']))
        else:
            messages.append(HumanMessage(content=message))

        try:
            response = self.llm.invoke(messages)
            
            end_time = time.time()
            latency = end_time - start_time
            
            print(f"  - Result: Success | Latency: {latency:.2f}s")
            return response.content

        except Exception as e:
            print(f"  - [SOLAR-ERROR] Critical Error: {str(e)}")
            return "죄송합니다. 분석 중 오류가 발생했습니다."

solar_service = SolarService()