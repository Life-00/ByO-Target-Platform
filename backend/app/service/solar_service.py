import time
from typing import Optional, List, Dict

from langchain_upstage import ChatUpstage
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.core.config import settings
from app.service.rag_service import rag_service


class SolarService:
    def __init__(self):
        self.llm = ChatUpstage(api_key=settings.UPSTAGE_API_KEY, model=settings.UPSTAGE_MODEL)
        print(f"[{time.strftime('%H:%M:%S')}] [SOLAR] Init (model={settings.UPSTAGE_MODEL})")

    async def get_chat_response(
        self,
        user_email: str,
        message: str,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        use_rag: bool = False,
    ) -> str:
        """
        - chat 모드: use_rag=False 권장
        - report 모드: use_rag=True 권장
        """
        msg_count = len(history) if history else 0
        print(f"[{time.strftime('%H:%M:%S')}] [SOLAR] Invoke (history={msg_count}, rag={use_rag})")
        start_time = time.time()

        # 1) RAG 컨텍스트(옵션)
        context = ""
        if use_rag and session_id:
            try:
                context = rag_service.get_relevant_context(message, session_id, user_email)
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] [SOLAR] RAG warn: {str(e)}")

        # 2) system prompt
        system_instruction = (
            "너는 전문적인 바이오 타겟 검증 어시스턴트이다. 연구원의 질문에 대해 과학적 근거를 바탕으로 친절하게 답변하라."
        )
        if context:
            system_instruction += (
                f"\n\n[참고 문서 내용]\n{context}\n\n"
                "위의 [참고 문서 내용]에 사용자의 질문과 관련된 정보가 있다면 이를 우선적으로 활용하여 답변하라."
            )

        messages = [SystemMessage(content=system_instruction)]

        # 3) history 추가
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") in ("ai", "assistant"):
                    messages.append(AIMessage(content=msg.get("content", "")))

        # ✅ 4) 현재 user message는 항상 마지막에 추가 (기존 버그 수정)
        messages.append(HumanMessage(content=message))

        try:
            response = self.llm.invoke(messages)
            latency = time.time() - start_time
            print(f"[{time.strftime('%H:%M:%S')}] [SOLAR] OK ({latency:.2f}s)")
            return response.content
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] [SOLAR] ERROR: {str(e)}")
            return "죄송합니다. 분석 중 오류가 발생했습니다."


solar_service = SolarService()
