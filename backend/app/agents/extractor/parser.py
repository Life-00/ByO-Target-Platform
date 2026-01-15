# app/agents/extractor/parser.py

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from pydantic import BaseModel


def _strip_code_fences(text: str) -> str:
    s = (text or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _extract_json_object(text: str) -> str:
    s = _strip_code_fences(text)

    try:
        json.loads(s)
        return s
    except Exception:
        pass

    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start:end + 1].strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON object extracted from LLM response") from e

    raise ValueError("Failed to locate valid JSON object in LLM response")


def parse_json_response(text: str) -> Dict[str, Any]:
    payload = _extract_json_object(text)
    return json.loads(payload)


# ===== Models =====

class EffectModel(BaseModel):
    direction: Optional[str]
    target_outcome: Optional[str]
    rationale: Optional[str]
    confidence: Optional[float]


class StanceModel(BaseModel):
    polarity: Optional[str]
    strength: Optional[str]
    conditions: Optional[str]


class SalienceModel(BaseModel):
    level: Optional[str]
    reason: Optional[str]


class ExtractedClaim(BaseModel):
    claim: str

    effect: Optional[EffectModel]
    stance: Optional[StanceModel]
    salience: Optional[SalienceModel]

    evidence_level: Optional[str]
    confidence: Optional[float]
    notes: Optional[str]