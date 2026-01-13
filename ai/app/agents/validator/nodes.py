from __future__ import annotations
from collections import defaultdict
from typing import Dict, Any, List

from app.agents.validator.state import ValidatorState
from app.agents.validator.internal_models import CanonicalClaim
from app.schemas.fact import FactSet
from app.schemas.claim import ValidatedClaims, ValidatedClaim

from app.agents.validator.logic import (
    make_cluster_id,
    build_evidence,
    rule_consistency,
    keyword_risk,
)
from app.agents.validator.llm_core import build_plans, ToolPlan


def node_ingest(state: ValidatorState) -> ValidatorState:
    fact_set = state["fact_set"]
    if isinstance(fact_set, list):
        fact_set = FactSet(facts=fact_set)

    state["canonical_claims"] = [CanonicalClaim(f) for f in fact_set.facts]
    return state


def node_cluster(state: ValidatorState) -> ValidatorState:
    claims = state.get("canonical_claims", [])
    groups = defaultdict(list)
    for c in claims:
        groups[c.key_tuple].append(c)
    state["clusters"] = dict(groups)
    return state


def node_controller(state: ValidatorState) -> ValidatorState:
    clusters = state.get("clusters", {})
    if not clusters:
        state["llm_plans"] = {}
        state["llm_cluster_notes"] = {}
        return state

    cluster_summaries: Dict[str, Any] = {}
    for key, group in clusters.items():
        subj, obj, rel = key[0], key[1], key[2]
        cid = make_cluster_id(subj, obj, rel)

        samples = []
        for c in group[:6]:
            samples.append({
                "pmid": c.original_fact.pmid,
                "sentence_id": c.original_fact.sentence_id,
                "text": (c.original_fact.text or "")[:280],
                "raw_relation": c.original_fact.relation.type,
                "experiment_model": getattr(c.original_fact.experiment, "model", None),
            })

        polarities = sorted(list({int(c.polarity) for c in group}))
        levels = sorted(list({c.evidence_level.value for c in group}))

        cluster_summaries[cid] = {
            "cluster": {"subject": subj, "object": obj, "relation_family": rel},
            "features": {"polarities": polarities, "evidence_levels": levels, "n_evidence": len(group)},
            "evidence_samples": samples,
        }

    state["llm_plans"] = build_plans(cluster_summaries)
    state["llm_cluster_notes"] = {"n_clusters": len(cluster_summaries)}
    return state


def node_synthesize(state: ValidatorState) -> ValidatorState:
    clusters = state.get("clusters", {})
    plans = state.get("llm_plans", {}) or {}

    validated: List[ValidatedClaim] = []

    for key, group in clusters.items():
        subj, obj, rel = key[0], key[1], key[2]
        cid = make_cluster_id(subj, obj, rel)

        plan = ToolPlan.model_validate(plans.get(cid, ToolPlan().model_dump()))

        evidence_items, evidence_summary = build_evidence(group)

        consistency = rule_consistency(group) if plan.run_rule_consistency else "insufficient"
        if plan.override_consistency:
            consistency = plan.override_consistency

        risks = keyword_risk(group) if plan.run_keyword_risk else []

        normalized = f"{subj} {rel} {obj}".strip()
        validated.append(ValidatedClaim(
            claim_id=cid,
            normalized_claim=normalized,
            evidence=evidence_items,
            evidence_summary=evidence_summary,
            consistency=consistency,
            risk_signals=risks,
        ))

    state["validated_claims"] = ValidatedClaims(claims=validated)
    return state
