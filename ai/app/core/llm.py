from __future__ import annotations

import os
from openai import OpenAI

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

# OpenAI-compatible client (solar-pro-2)
llm_client = OpenAI(
    base_url="https://api.upstage.ai/v1",
    api_key=UPSTAGE_API_KEY,
)

DEFAULT_LLM_MODEL = "solar-pro"


def generate_text(prompt: str) -> str:
    """LLM text generation entrypoint"""
    resp = llm_client.chat.completions.create(
        model=DEFAULT_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content


def get_tokenizer():
    """필요할 때만 tokenizer 로딩"""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained("upstage/solar-pro-preview-instruct")
