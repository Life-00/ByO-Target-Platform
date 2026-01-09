import time
import os
from openai import OpenAI
from app.core.config import settings

class SolarService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.UPSTAGE_API_KEY,
            base_url=settings.UPSTAGE_BASE_URL
        )
        print(f"[{time.strftime('%H:%M:%S')}] [SOLAR-SERVICE] Service Initialized.")

    async def get_chat_response(self, user_email: str, message: str):
        """
        Solar-Pro 모델을 사용하여 답변을 생성합니다.
        """
        print(f"\n[{time.strftime('%H:%M:%S')}] [SOLAR-LLM] Reasoning for user: {user_email}")
        print(f"  - User Message: {message[:50]}...")

        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=settings.UPSTAGE_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "너는 전문적인 바이오 타겟 검증 어시스턴트이다. 연구원의 질문에 대해 과학적 근거를 바탕으로 친절하게 답변하라."
                    },
                    {"role": "user", "content": message}
                ],
                stream=False
            )

            end_time = time.time()
            latency = end_time - start_time
            answer = response.choices[0].message.content
            
            print(f"  - Result: Success | Latency: {latency:.2f}s | Tokens: {response.usage.total_tokens}")
            return answer

        except Exception as e:
            print(f"  - Result: Critical Error during LLM reasoning: {str(e)}")
            return "죄송합니다. 분석 중 오류가 발생했습니다."

solar_service = SolarService()