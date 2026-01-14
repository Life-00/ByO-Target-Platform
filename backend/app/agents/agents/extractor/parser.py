# app/agents/extractor/parser.py

import json
from typing import Any, Dict, Optional


def parse_json_response(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")


def normalize_enum(
    value: Optional[str],
    allowed: set,
    default: str,
) -> str:
    if not value:
        return default
    value = value.strip()
    return value if value in allowed else default


def normalize_optional_str(value: Any) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip()
    return value if value else None


def clamp_confidence(value: Any, default: float = 0.5) -> float:
    try:
        v = float(value)
        return max(0.0, min(1.0, v))
    except Exception:
        return default
