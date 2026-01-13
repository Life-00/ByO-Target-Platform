import os
import pytest


def test_generate_text_returns_string():
    # API 키 없으면 LLM 테스트는 스킵
    if not os.getenv("UPSTAGE_API_KEY"):
        pytest.skip("UPSTAGE_API_KEY not set")

    # import를 함수 안으로 넣어서 pytest 수집 단계(collection)에서 ImportError 방지
    from app.core.llm import generate_text

    result = generate_text("hello")
    assert isinstance(result, str)
    assert len(result) > 0
