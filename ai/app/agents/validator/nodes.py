from __future__ import annotations
import re
import hashlib
from collections import defaultdict
from typing import List, Dict, Any

from app.schemas.claim import ValidatedClaims, ValidatedClaim, EvidenceItem, RiskSignal
from app.agents.validator.state import ValidatorState
from app.agents.validator.internal_models import CanonicalClaim, Polarity, EvidenceLevel
from app.schemas.fact import FactSet

# Configuration
RISK_KEYWORDS = {
    # 독성/안전성 신호
    "toxicity": [
        "toxicity", "toxic", "adverse", "side effect", "safety",
        "hepatotoxic", "nephrotoxic", "cardiotoxic", "neurotoxic",
        "off-target", "cytotoxic"
    ],

    # 효능 부족/실패 신호
    "efficacy_failure": [
        "failed", "failure", "ineffective", "no effect", "lack of efficacy",
        "did not improve", "not significant"
    ],

    # 모순/불일치(선택: Validator의 consistency와 중복될 수 있어 optional)
    "inconsistency_signal": [
        "contradict", "inconsistent", "mixed results", "conflicting"
    ],
}

def node_ingest(state: ValidatorState) -> ValidatorState:
    """Ingest Facts and normalize to CanonicalClaims"""
    fact_set = state["fact_set"]

    if isinstance(fact_set, list):
        fact_set = FactSet(facts=fact_set)

    canonical_claims = [CanonicalClaim(f) for f in fact_set.facts]
    state["canonical_claims"] = canonical_claims
    return state

def node_cluster(state: ValidatorState) -> ValidatorState:
    """Group CanonicalClaims by semantic key"""
    claims = state.get("canonical_claims", [])
    groups = defaultdict(list)
    for c in claims:
        groups[c.key_tuple].append(c)
    state["clusters"] = dict(groups)
    return state

def node_synthesize(state: ValidatorState) -> ValidatorState:
    """Synthesize clusters into ValidatedClaims"""
    clusters = state.get("clusters", {})
    validated_list = []
    
    for key, group in clusters.items():
        val_claim = _synthesize_single_cluster(key, group)
        validated_list.append(val_claim)
        
    state["validated_claims"] = ValidatedClaims(claims=validated_list)
    return state

# --- Helper Functions (Private to Nodes) ---

def _destructure_key(key):
    return key[0], key[1], key[2]

def _synthesize_single_cluster(key: tuple, group: List[CanonicalClaim]) -> ValidatedClaim:
    subj, obj, rel = _destructure_key(key)
    
    # 1. Consistency
    polarities = {c.polarity for c in group}
    if polarities == {Polarity.POSITIVE} or polarities == {Polarity.NEGATIVE}:
        consistency = "consistent"
    elif Polarity.POSITIVE in polarities and Polarity.NEGATIVE in polarities:
        consistency = "conflicting"
    else:
        consistency = "insufficient"

    # 2. Evidence
    evidence_list = []
    evidence_counts = {"in_vitro": 0, "in_vivo": 0, "clinical": 0}
    
    for c in group:
        lvl_str = c.evidence_level.value.lower().replace(" ", "_")
        if lvl_str in evidence_counts:
            evidence_counts[lvl_str] += 1
            
        display_lvl = c.evidence_level.value.lower()
        ev_item = EvidenceItem(
            pmid=c.original_fact.pmid,
            sentence_id=c.original_fact.sentence_id,
            experiment_level=display_lvl
        )
        evidence_list.append(ev_item)

    # 3. Risks
    aggregated_risks: dict[str, set[str]] = {}
    for c in group:
        risk_hits = _detect_risks(c.original_fact.text)
        for risk_type, keywords in risk_hits.items():
            aggregated_risks.setdefault(risk_type, set()).update(keywords)

    risk_signals = [
        RiskSignal(
            type=risk_type,
            keywords=sorted(list(keywords))
        )
        for risk_type, keywords in aggregated_risks.items()
    ]

    # 4. Construct
    normalized_text = f"{subj} {rel} {obj}".strip()
    cluster_id = hashlib.md5(f"{subj}|{obj}|{rel}".encode()).hexdigest()
    
    return ValidatedClaim(
        claim_id=cluster_id,
        normalized_claim=normalized_text,
        evidence=evidence_list,
        evidence_summary=evidence_counts,
        consistency=consistency,
        risk_signals=risk_signals
    )

def _detect_risks(text: str) -> dict[str, list[str]]:
    """
    Detect risk-related keywords in text.
    Returns:
      {
        "toxicity": ["toxicity", "hepatotoxic"],
        "efficacy_failure": ["no effect"]
      }
    """
    if not text:
        return {}

    text = text.lower()
    detected: dict[str, list[str]] = {}

    for risk_type, keywords in RISK_KEYWORDS.items():
        hits = []
        for kw in keywords:
            if kw in text:
                hits.append(kw)

        if hits:
            detected[risk_type] = sorted(set(hits))

    return detected

