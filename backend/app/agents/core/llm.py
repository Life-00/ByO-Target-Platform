# app/core/llm.py
from openai import OpenAI
from app.core.config import settings  # ✅ 설정 파일 사용

# OpenAI-compatible client (solar-pro2)
DEFAULT_LLM_MODEL = "solar-pro2"

# settings에서 API 키 가져오기
llm_client = OpenAI(
    base_url="https://api.upstage.ai/v1",
    api_key=settings.UPSTAGE_API_KEY,
)

def call_llm(
    prompt: str,
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.0,
) -> str:
    """
    Call LLM with a single user prompt.
    Returns raw text response.
    """
    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content.strip()