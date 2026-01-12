import time
from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings
from app.service.rag_service import rag_service

class AgentService:
    def __init__(self):
        # 현재는 Solar-Pro를 기본 엔진으로 사용
        # 나중에 에이전트 팀의 Graph나 Logic이 여기 초기화됩니다.
        self.llm = ChatUpstage(
            api_key=settings.UPSTAGE_API_KEY,
            model=settings.UPSTAGE_MODEL
        )
        print(f"[{time.strftime('%H:%M:%S')}] [AGENT-SERVICE] Base Engine Ready.")

    async def process_request(self, email: str, session_id: str, message: str):
        """
        이 함수가 에이전트 팀의 코드가 이식될 '표준 소켓'입니다.
        """
        print(f"\n[{time.strftime('%H:%M:%S')}] [AGENT-LOGIC] Thinking... (User: {email})")
        
        # 1. 에이전트가 사용할 도구(RAG)로부터 컨텍스트 확보
        context = rag_service.get_relevant_context(message, session_id, email)
        
        # 2. 에이전트의 사고 루프 (현재는 단순 RAG 응답)
        # 나중에 에이전트 팀이 이 부분을 LangGraph의 'app.ainvoke()' 등으로 교체하게 됩니다.
        system_prompt = f"너는 전문 바이오 에이전트이다. 다음 내용을 참고해라: \n{context}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"  - [AGENT-ERROR] {str(e)}")
            return "에이전트가 응답 생성에 실패했습니다."

# 전역 인스턴스 생성
agent_service = AgentService()