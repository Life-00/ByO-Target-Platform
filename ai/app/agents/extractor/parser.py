# app/agents/extractor/parsers.py
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


def _extract_json_object(text: str) -> str:
    """
    Extract the first JSON object found in a string.
    Handles cases where LLM outputs extra text.
    """
    text = text.strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return match.group(0)


def parse_json_response(text: str) -> Dict[str, Any]:
    json_str = _extract_json_object(text)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}; raw={json_str[:200]}")


def normalize_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        return s if s else None
    return str(value).strip() or None


def normalize_enum(value: Any, allowed: set[str], default: str) -> str:
    if not isinstance(value, str):
        return default
    v = value.strip().lower()
    return v if v in allowed else default


def clamp_confidence(value: Any, default: float = 0.5) -> float:
    try:
        v = float(value)
    except Exception:
        return default
    return max(0.0, min(1.0, v))
