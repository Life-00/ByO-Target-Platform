# app/core/llm.py
from openai import OpenAI
from app.core.config import settings

from transformers import AutoTokenizer  # ✅ 추가

DEFAULT_LLM_MODEL = "solar-pro2"

llm_client = OpenAI(
    base_url="https://api.upstage.ai/v1",
    api_key=settings.UPSTAGE_API_KEY,
)

# ✅ 추가: tokenizer + limit
TOKENIZER = AutoTokenizer.from_pretrained("upstage/solar-pro2-tokenizer")
MAX_TOKEN_LIMIT = 62000  # 65536보다 여유 있게

def _truncate_prompt(prompt: str, max_tokens: int = MAX_TOKEN_LIMIT) -> str:
    ids = TOKENIZER.encode(prompt)
    if len(ids) <= max_tokens:
        return prompt
    # 뒤쪽 유지(최근 내용 유지)
    return TOKENIZER.decode(ids[-max_tokens:])

def call_llm(
    prompt: str,
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.0,
) -> str:
    # ✅ 핵심: 보내기 전에 자른다
    prompt = _truncate_prompt(prompt)

    response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()
