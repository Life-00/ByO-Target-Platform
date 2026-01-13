import time
from app.agents.dialogue.agent import DialogueAgent
from app.schemas.message import UserMessage, SystemResponse

class AgentService:
    def __init__(self):
        print(f"[{time.strftime('%H:%M:%S')}] [AGENT-SERVICE] Initializing DialogueAgent...")
        self.agent = DialogueAgent()

    async def process_request(self, user_email: str, message: str, session_id: str, history: list = None) -> str:
        
        print(f"\n[{time.strftime('%H:%M:%S')}] [AGENT-SERVICE] Session: {session_id}")

        # DialogueAgent의 입력 포맷인 UserMessage 생성
        # context에 필요한 정보들을 담아서 넘깁니다.
        user_msg_obj = UserMessage(
            session_id=session_id,
            message=message,
            context={
                "user_email": user_email,
                "history": history
            }
        )

        try:
            # DialogueAgent 실행 (내부에서 Orchestrator 호출)
            # agent.run()이 동기 함수라면 바로 호출
            system_response: SystemResponse = self.agent.run(user_message=user_msg_obj)

            # 결과 처리
            reply_text = system_response.message
            
            # 로그 출력
            print(f"[{time.strftime('%H:%M:%S')}] [AGENT-RESPONSE] {system_response.type}: {reply_text}")
            
            return reply_text

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[{time.strftime('%H:%M:%S')}] [AGENT-ERROR] {str(e)}")
            return "시스템 오류가 발생했습니다."

agent_service = AgentService()