# app/utils/tokenizer.py
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

import os

# Transformers가 없을 수도 있으니 안전하게 import
try:
    from transformers import AutoTokenizer
except Exception:  # pragma: no cover
    AutoTokenizer = None  # type: ignore


# ---------------------------
# Config
# ---------------------------
DEFAULT_TOKENIZER_NAME = os.getenv("TOKENIZER_NAME", "gpt2")
# 업스테이지 임베딩 제한(4000) 대비 안전한 값: 2800
DEFAULT_MAX_TOKENS = int(os.getenv("EMBEDDING_MAX_TOKENS", "2800"))
DEFAULT_OVERLAP_TOKENS = int(os.getenv("EMBEDDING_OVERLAP_TOKENS", "150"))


@dataclass
class TokenizerInfo:
    name: str
    is_fallback: bool


@lru_cache(maxsize=1)
def get_tokenizer() -> Tuple[object, TokenizerInfo]:
    """
    프로젝트 어디서든 토크나이저를 공유해서 로드 비용 줄이기.
    - TOKENIZER_NAME env로 교체 가능
    - transformers 없으면 fallback 토크나이저를 사용
    """
    name = DEFAULT_TOKENIZER_NAME

    if AutoTokenizer is None:
        return _FallbackTokenizer(), TokenizerInfo(name="fallback-whitespace", is_fallback=True)

    try:
        tok = AutoTokenizer.from_pretrained(name, use_fast=True)
        return tok, TokenizerInfo(name=name, is_fallback=False)
    except Exception:
        # 로드 실패 시 fallback
        return _FallbackTokenizer(), TokenizerInfo(name="fallback-whitespace", is_fallback=True)


def count_tokens(text: str) -> int:
    """
    텍스트 토큰 개수 계산 (가능하면 실제 tokenizer 기준).
    """
    text = (text or "").strip()
    if not text:
        return 0

    tok, info = get_tokenizer()
    if info.is_fallback:
        # 대충 단어 단위
        return len(text.split())

    # transformers tokenizer
    try:
        ids = tok.encode(text, add_special_tokens=False)  # type: ignore
        return len(ids)
    except Exception:
        return len(text.split())


def chunk_text_by_tokens(
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> List[str]:
    """
    토큰 기준 chunking.
    - overlap_tokens: 문맥 유지용(추천 100~300)
    - max_tokens: 업스테이지 4096 제한이면 3200~3500 권장
    """
    text = (text or "").strip()
    if not text:
        return []

    if max_tokens <= 0:
        return [text]

    overlap_tokens = max(0, min(overlap_tokens, max_tokens - 1))

    tok, info = get_tokenizer()

    # fallback: 글자수 기반(대충) chunking
    if info.is_fallback:
        # 대략 토큰=단어라 가정하고 단어 단위로 자르기
        words = text.split()
        if not words:
            return []
        chunks: List[str] = []
        step = max(1, max_tokens - overlap_tokens)
        i = 0
        while i < len(words):
            chunk_words = words[i : i + max_tokens]
            chunks.append(" ".join(chunk_words))
            i += step
        return chunks

    # transformers: 진짜 토큰 ids 기준으로 자르기
    try:
        ids: List[int] = tok.encode(text, add_special_tokens=False)  # type: ignore
    except Exception:
        # encode 실패 시 fallback
        return _simple_char_chunks(text, approx_chunk_chars=2000, overlap_chars=200)

    if not ids:
        return []

    chunks: List[str] = []
    step = max(1, max_tokens - overlap_tokens)

    start = 0
    while start < len(ids):
        end = min(len(ids), start + max_tokens)
        sub_ids = ids[start:end]
        try:
            chunk = tok.decode(sub_ids, skip_special_tokens=True)  # type: ignore
        except Exception:
            # decode 실패 시 문자 기반으로라도 대체
            chunk = text
        chunk = (chunk or "").strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def safe_chunks_for_embedding(
    prefix: str,
    text: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> List[str]:
    """
    prefix(예: '[[Page 3]]\\n')를 붙인 최종 텍스트가 max_tokens를 넘지 않도록 쪼개기.
    - prefix 토큰 수만큼 max_tokens를 자동 감소시켜 chunking 수행
    """
    prefix = prefix or ""
    prefix_tokens = count_tokens(prefix)

    # prefix만으로도 너무 크면 그냥 prefix 축소
    if prefix_tokens >= max_tokens:
        # prefix를 안전하게 잘라서 사용
        trimmed_prefix = _truncate_to_tokens(prefix, max_tokens=max(1, max_tokens // 2))
        prefix = trimmed_prefix
        prefix_tokens = count_tokens(prefix)

    body_budget = max(1, max_tokens - prefix_tokens)

    body_chunks = chunk_text_by_tokens(
        text=text,
        max_tokens=body_budget,
        overlap_tokens=min(overlap_tokens, max(0, body_budget - 1)),
    )
    return [f"{prefix}{c}" for c in body_chunks]


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """토큰 기준으로 텍스트 자르기"""
    text = (text or "").strip()
    if not text:
        return ""
    if max_tokens <= 0:
        return ""

    tok, info = get_tokenizer()
    if info.is_fallback:
        return " ".join(text.split()[:max_tokens])

    try:
        ids = tok.encode(text, add_special_tokens=False)  # type: ignore
        ids = ids[:max_tokens]
        return tok.decode(ids, skip_special_tokens=True).strip()  # type: ignore
    except Exception:
        return text[: max(1, min(len(text), max_tokens * 4))].strip()


def _simple_char_chunks(text: str, approx_chunk_chars: int = 2000, overlap_chars: int = 200) -> List[str]:
    """문자 기반 간단한 chunking (fallback)"""
    text = (text or "").strip()
    if not text:
        return []
    approx_chunk_chars = max(200, approx_chunk_chars)
    overlap_chars = max(0, min(overlap_chars, approx_chunk_chars - 1))

    chunks: List[str] = []
    step = max(1, approx_chunk_chars - overlap_chars)
    i = 0
    while i < len(text):
        chunk = text[i : i + approx_chunk_chars].strip()
        if chunk:
            chunks.append(chunk)
        i += step
    return chunks


class _FallbackTokenizer:
    """
    transformers 없을 때용: encode/decode 인터페이스 흉내
    """
    def encode(self, text: str, add_special_tokens: bool = False) -> List[int]:
        # 단어를 토큰으로 가정하고 index를 id로 가정
        words = (text or "").split()
        return list(range(len(words)))

    def decode(self, ids: List[int], skip_special_tokens: bool = True) -> str:
        # decode는 불가능하니 빈 문자열(실사용 안 함)
        return ""
