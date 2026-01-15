from app.core.llm import call_llm

# 아주 큰 텍스트 생성 (충분히 크게)
big_text = "A" * 3_000_000

prompt = f"""
Return STRICT JSON only:
{{"ok": true}}

Below is huge content:
{big_text}
"""

print(call_llm(prompt))
