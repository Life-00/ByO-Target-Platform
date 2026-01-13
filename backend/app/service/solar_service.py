import time
from typing import Optional, List, Dict
from uuid import UUID

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
        session_id: Optional[UUID] = None,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None,
    ) -> str:
        
        msg_count = len(history) if history else 0
        print(f"[{time.strftime('%H:%M:%S')}] [SOLAR] Invoke (session={session_id}, history={msg_count}, context_len={len(context) if context else 0})")
        start_time = time.time()

        # 1) 시스템 프롬프트 구성 (TV-A 페르소나)
        base_system_prompt = (
            "당신은 'TV-A(Target Validation Assistant)'입니다. "
            "사용자의 바이오/제약 연구를 돕는 AI 에이전트입니다. "
            "주어진 [Context]를 바탕으로 질문에 대해 구체적이고 전문적인 답변을 제공하세요. "
            "스스로를 ChatGPT나 다른 모델이라고 소개하지 마세요."
        )

        # 2) Context 주입 및 ✅ [파일명 인용 지시 추가]
        if context:
            base_system_prompt += (
                f"\n\n[Context]\n{context}\n\n"
                "위의 [Context] 내용을 분석하여 답변의 근거로 사용하세요. "
                "📢 중요: 답변할 때 반드시 해당 정보가 포함된 '파일명'을 언급하여 출처를 명확히 하세요. "
                "(예: 'OOO.pdf 파일에 따르면, ...')"
            )

        messages = [SystemMessage(content=base_system_prompt)]

        # 3) 대화 내역(History) 추가
        if history:
            for msg in history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role in ("ai", "assistant"):
                    messages.append(AIMessage(content=content))
        
        # 4) 현재 사용자 질문 추가
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