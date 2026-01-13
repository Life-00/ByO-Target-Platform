from __future__ import annotations
import hashlib
from typing import List, Tuple, Dict

from app.agents.validator.internal_models import CanonicalClaim, Polarity, EvidenceLevel
from app.schemas.claim import EvidenceItem, RiskSignal


RISK_KEYWORDS: Dict[str, List[str]] = {
    "toxicity": ["toxicity", "toxic", "adverse", "side effect", "hepatotoxic", "nephrotoxic", "off-target", "cytotoxic"],
    "failure": ["failed", "failure", "ineffective", "no effect", "lack of efficacy", "not significant"],
    "inconsistency": ["contradict", "inconsistent", "mixed results", "conflicting"],
}


def make_cluster_id(subj: str, obj: str, rel: str) -> str:
    return hashlib.md5(f"{subj}|{obj}|{rel}".encode()).hexdigest()


def rule_consistency(group: List[CanonicalClaim]) -> str:
    polarities = {c.polarity for c in group}
    if polarities == {Polarity.POSITIVE} or polarities == {Polarity.NEGATIVE}:
        return "consistent"
    if Polarity.POSITIVE in polarities and Polarity.NEGATIVE in polarities:
        return "conflicting"
    return "insufficient"


def normalize_experiment_level(level: EvidenceLevel) -> str:
    v = (level.value or "").lower()
    if "vitro" in v:
        return "in vitro"
    if "vivo" in v:
        return "in vivo"
    if "clinical" in v or "human" in v:
        return "clinical"
    return "in vitro" if v == "" else v


def build_evidence(group: List[CanonicalClaim]) -> Tuple[List[EvidenceItem], Dict[str, int]]:
    items: List[EvidenceItem] = []
    summary = {"in_vitro": 0, "in_vivo": 0, "clinical": 0}

    for c in group:
        lvl = normalize_experiment_level(c.evidence_level)
        if lvl == "in vitro":
            summary["in_vitro"] += 1
        elif lvl == "in vivo":
            summary["in_vivo"] += 1
        elif lvl == "clinical":
            summary["clinical"] += 1

        items.append(EvidenceItem(
            pmid=c.original_fact.pmid,
            sentence_id=c.original_fact.sentence_id,
            experiment_level=lvl,
        ))

    return items, summary


def keyword_risk(group: List[CanonicalClaim]) -> List[RiskSignal]:
    """
    ✅ claim.py 스키마 정합: RiskSignal(type, pmid, sentence_id)
    """
    out: List[RiskSignal] = []
    seen = set()

    for c in group:
        text = (c.original_fact.text or "").lower()
        if not text:
            continue

        for risk_type, kws in RISK_KEYWORDS.items():
            if any(kw in text for kw in kws):
                key = (risk_type, c.original_fact.pmid, c.original_fact.sentence_id)
                if key in seen:
                    continue
                seen.add(key)
                out.append(RiskSignal(
                    type=risk_type,
                    pmid=c.original_fact.pmid,
                    sentence_id=c.original_fact.sentence_id,
                ))

    return out
