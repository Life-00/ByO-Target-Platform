from __future__ import annotations
import hashlib
from collections import defaultdict
from typing import List, Dict, Any

from app.schemas.claim import ValidatedClaims, ValidatedClaim, EvidenceItem, RiskSignal
from app.agents.validator.state import ValidatorState
from app.agents.validator.internal_models import CanonicalClaim, Polarity, EvidenceLevel

# Configuration
RISK_KEYWORDS = {
    "mobility": ["toxicity", "toxic", "adverse", "side effect", "poison"], # Mapped to 'toxicity'
    "failure": ["fail", "no effect", "ineffective", "resistance"],
    "inconsistency": ["conflicting", "controversial"]
}

def node_ingest(state: ValidatorState) -> ValidatorState:
    """Ingest Facts and normalize to CanonicalClaims"""
    fact_set = state["fact_set"]
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
    if Polarity.POSITIVE in polarities and Polarity.NEGATIVE in polarities:
        consistency = "conflicting"
    elif len(polarities) > 1:
        consistency = "consistent"
    else:
        consistency = "consistent"
        
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
    risk_signals = _detect_risks(group)
    if risk_signals:
        if any(r.type == "failure" for r in risk_signals) and consistency == "consistent":
             consistency = "insufficient"

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

def _detect_risks(group: List[CanonicalClaim]) -> List[RiskSignal]:
    signals = []
    seen = set()
    
    for c in group:
        text = c.original_fact.text.lower()
        for r_type, keywords in RISK_KEYWORDS.items():
            if any(k in text for k in keywords):
                mapped_type = r_type
                if r_type == "mobility": mapped_type = "toxicity"
                
                unique_key = (mapped_type, c.original_fact.pmid)
                if unique_key in seen:
                    continue
                seen.add(unique_key)
                
                signals.append(RiskSignal(
                    type=mapped_type,
                    pmid=c.original_fact.pmid,
                    sentence_id=c.original_fact.sentence_id
                ))
    return signals
