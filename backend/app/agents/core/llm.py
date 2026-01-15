# app/core/llm.py

from openai import OpenAI
from app.config.env import UPSTAGE_API_KEY
import os

from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("upstage/solar-pro2-tokenizer")


UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

# OpenAI-compatible client (solar-pro2)
DEFAULT_LLM_MODEL = "solar-pro2"

llm_client = OpenAI(
    base_url="https://api.upstage.ai/v1",
    api_key=UPSTAGE_API_KEY,
)


def call_llm(
    prompt: str,
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.0,
) -> str:
    # MVP 기준: system/history 없음
    safe_prompt = truncate_tokens_if_needed(
        tokenizer=tokenizer,
        agent_instructions="",   # 지금은 system 없음
        messages=[],             # history 없음
        content=prompt,
        max_token_limit=62000,   # solar-pro2 여유 마진
    )

    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": safe_prompt}
        ],
        temperature=temperature,
    )

    return response.choices[0].message.content.strip()

def truncate_tokens_if_needed(
    tokenizer,
    agent_instructions,
    messages,
    content,
    max_token_limit=60000,
):
    inputs = tokenizer.apply_chat_template(
        [{"role": "system", "content": agent_instructions}] + messages,
        tokenize=True,
    )
    base_token_numbers = len(inputs)

    encoded_content = tokenizer.encode(content)
    content_token_numbers = len(encoded_content)

    if base_token_numbers + content_token_numbers > max_token_limit:
        allowed_tokens = max_token_limit - base_token_numbers
        if allowed_tokens <= 0:
            return ""
        truncated_tokens = encoded_content[-allowed_tokens:]
        return tokenizer.decode(truncated_tokens)

    return content
