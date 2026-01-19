# app/agents/synthesizer/report_policy.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

# Report-grade Contract (스키마/키/포맷 불변)
REQUIRED_SECTION_KEYS: Set[str] = {
    "target_profile",
    "key_claims",
    "evidence_level_summary",
    "risk_signals",
    "next_validation_steps",
}

# Assembler Evidence 출력 포맷(변경 금지)
REQUIRED_EVIDENCE_MARKERS: List[str] = [
    "- Evidence:",
    '- Quote: "',
    "Source: PMID:",
]

HITS_EMPTY_POLICY_ID = "cannot_say_report"


@dataclass(frozen=True)
class ReportPolicy:
    """
    Report Agent(강화된 Synthesizer)가 반드시 지켜야 하는 규칙 집합.
    - 스키마 불변
    - 섹션 키 불변
    - Evidence 표기 포맷 불변
    """
    required_section_keys: Set[str] = field(default_factory=lambda: set(REQUIRED_SECTION_KEYS))
    required_evidence_markers: List[str] = field(default_factory=lambda: list(REQUIRED_EVIDENCE_MARKERS))
    hits_empty_policy_id: str = HITS_EMPTY_POLICY_ID
    strict: bool = True


# ✅ post_validate에서 import하는 이름을 반드시 제공
DEFAULT_POLICY = ReportPolicy()


def policy_summary(policy: ReportPolicy = DEFAULT_POLICY) -> Dict[str, object]:
    return {
        "required_section_keys": sorted(list(policy.required_section_keys)),
        "required_evidence_markers": list(policy.required_evidence_markers),
        "hits_empty_policy_id": policy.hits_empty_policy_id,
        "strict": policy.strict,
    }
