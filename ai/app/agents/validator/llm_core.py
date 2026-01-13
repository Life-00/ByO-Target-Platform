from __future__ import annotations
import json
from typing import Dict, Any, List, Optional, Literal

from pydantic import BaseModel, Field

from app.core.llm import llm_client, DEFAULT_LLM_MODEL


class ToolPlan(BaseModel):
    run_rule_consistency: bool = True
    run_keyword_risk: bool = True

    override_consistency: Optional[Literal["consistent", "conflicting", "insufficient"]] = None
    override_rationale_evidence: List[Dict[str, str]] = Field(default_factory=list)  # [{"pmid","sentence_id"}]
    note: str = ""


class ClusterPlanOutput(BaseModel):
    plans: Dict[str, ToolPlan]  # cluster_id -> plan


def llm_json(system: str, user_payload: dict, model: str = DEFAULT_LLM_MODEL) -> dict:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]
    try:
        resp = llm_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        resp = llm_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )
        return json.loads(resp.choices[0].message.content)


def build_plans(cluster_summaries: Dict[str, Any]) -> Dict[str, dict]:
    system = (
        "You are the ValidatorAgent core controller.\n"
        "Decide WHICH deterministic tools to run per cluster.\n"
        "Do NOT invent biomedical facts.\n"
        "Do NOT create evidence IDs that are not provided.\n"
        "Return STRICT JSON only.\n"
        "Tools available: rule_consistency, keyword_risk.\n"
        "If overriding consistency, cite evidence IDs from evidence_samples.\n"
        "Output schema MUST follow the provided JSON schema."
    )

    payload = {
        "clusters": cluster_summaries,
        "toolplan_schema": ClusterPlanOutput.model_json_schema(),
    }

    try:
        data = llm_json(system, payload)
        parsed = ClusterPlanOutput.model_validate(data)
        return {k: v.model_dump() for k, v in parsed.plans.items()}
    except Exception:
        # fallback: 기본 플랜
        return {cid: ToolPlan().model_dump() for cid in cluster_summaries.keys()}
