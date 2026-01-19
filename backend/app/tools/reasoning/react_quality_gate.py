# app/tools/reasoning/react_quality_gate.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
import json
import re


NextAction = Literal[
    "increase_top_k",
    "rewrite_query",
    "diversify_sources",
    "focus_sections",
    "ask_user_clarification",
    "stop",
]


@dataclass
class EvidenceItem:
    """
    Generic evidence unit shared across agents.
    """
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityGateResult:
    accept: bool
    confidence: float  # 0.0 ~ 1.0
    failure_reasons: List[str]

    next_action: Optional[NextAction] = None
    action_params: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    llm_raw: Optional[Dict[str, Any]] = None


# -----------------------------
# Main entry
# -----------------------------

async def react_quality_gate(
    *,
    task_goal: str,
    query: str,
    evidence_items: List[EvidenceItem],
    llm_service: Any,
    max_items: int = 12,
) -> QualityGateResult:
    """
    PERMISSIVE Quality Gate - Always accepts with sufficient evidence items
    
    This gate prioritizes user satisfaction over strict quality checks.
    Use for development/testing or when you want the agent to always attempt answers.
    """

    if not evidence_items:
        return QualityGateResult(
            accept=False,
            confidence=0.0,
            failure_reasons=["no_evidence"],
            next_action="increase_top_k",
            action_params={"top_k_delta": 5},
            rationale="No evidence items provided."
        )

    # If we have at least some evidence, ACCEPT it
    num_items = len(evidence_items)
    
    return QualityGateResult(
        accept=True,  # Always accept if we have evidence
        confidence=min(1.0, 0.5 + (num_items / 20.0)),  # Increase confidence with more items
        failure_reasons=[],  # No failure reasons
        next_action=None,  # No next action needed
        action_params={},
        rationale=f"Permissive gate: Accepting {num_items} evidence item(s) as sufficient.",
        llm_raw={"mode": "permissive_accept"},
    )


# -----------------------------
# Prompt
# -----------------------------

_SYSTEM_PROMPT = """
You are a strict quality auditor for a document-grounded research assistant.

You MUST NOT answer the user's question.
You MUST NOT add new facts or interpretations.
You ONLY evaluate whether the provided evidence is sufficient and appropriate.

Your role is to help prevent hallucination and overconfidence.
"""


def _build_judge_prompt(
    *,
    task_goal: str,
    query: str,
    evidence_summaries: List[Dict[str, Any]],
) -> str:
    payload = {
        "task_goal": task_goal,
        "user_query": query,
        "evidence_summaries": evidence_summaries,
        "evaluation_criteria": [
            "Relevance: Does the evidence directly address the query?",
            "Evidence sufficiency: Are there enough concrete excerpts?",
            "Coverage: Is evidence drawn from multiple documents or sections?",
            "Risk of hallucination: Would answering now require speculation?",
        ],
        "output_schema": {
            "accept": "boolean",
            "confidence": "number (0.0-1.0)",
            "failure_reasons": "string[]",
            "next_action": [
                "increase_top_k",
                "rewrite_query",
                "diversify_sources",
                "focus_sections",
                "ask_user_clarification",
                "stop"
            ],
            "action_params": "object",
            "rationale": "string"
        },
        "rules": [
            "Base your judgment ONLY on the provided evidence summaries.",
            "If evidence is insufficient, suggest exactly ONE next_action.",
            "Do NOT answer the query.",
            "Output ONLY valid JSON."
        ]
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# -----------------------------
# Utils
# -----------------------------

def _safe_json_parse(text: str) -> Any:
    if not text:
        return None
    t = text.strip()

    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()

    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None