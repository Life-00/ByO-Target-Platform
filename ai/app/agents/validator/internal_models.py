from __future__ import annotations
from typing import List, Dict, Any, Optional
import hashlib
from enum import Enum
from collections import defaultdict

# Internal Enums (Copied from previous agent.py)
class Polarity(int, Enum):
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1

class EvidenceLevel(str, Enum):
    IN_VITRO = "In Vitro"
    IN_VIVO = "In Vivo"
    CLINICAL = "Clinical"
    UNKNOWN = "Unknown"

    @staticmethod
    def rank(x: "EvidenceLevel") -> int:
        return {
            EvidenceLevel.UNKNOWN: 0,
            EvidenceLevel.IN_VITRO: 1,
            EvidenceLevel.IN_VIVO: 2,
            EvidenceLevel.CLINICAL: 3,
        }[x]

    def __lt__(self, other: "EvidenceLevel"):
        return EvidenceLevel.rank(self) < EvidenceLevel.rank(other)

class CanonicalClaim:
    """
    Internal representation of a claim for graph building.
    """
    def __init__(self, fact: Any): # Type Any to avoid circular import with app.schemas.fact if not needed, but we can import
        self.original_fact = fact
        self.subj = self._extract_subject(fact)
        self.obj = self._extract_object(fact)
        raw_rel = fact.relation.type.lower()
        self.polarity = self._normalize_polarity(raw_rel)

        # relatation_family
        if raw_rel in ("increase", "decrease"):
            self.relation_type = "regulation"
        elif raw_rel in ("association", "no_effect"):
            self.relation_type = raw_rel
        else:
            self.relation_type = "unknown"
        self.evidence_level = self._normalize_stage(fact.experiment.model)
        self.id = self._compute_id()

    @property
    def key_tuple(self):
        return (self.subj, self.obj, self.relation_type)

    def _extract_subject(self, fact) -> str:
        compounds = getattr(fact.entities, "compound", None) or []
        if compounds:
            return compounds[0].lower().strip()
        targets = getattr(fact.entities, "target", None) or []
        if targets:
            return targets[0].lower().strip()
        return "unknown_subject"

    def _extract_object(self, fact) -> str:
        rel_obj = getattr(fact.relation, "object", None)
        if rel_obj:
            return rel_obj.lower().strip()
        targets = getattr(fact.entities, "target", None) or []
        if targets:
            return targets[0].lower().strip()
        diseases = getattr(fact.entities, "disease", None) or []
        if diseases:
            return diseases[0].lower().strip()
        return "unknown_object"


    def _normalize_polarity(self, rel_type: str) -> Polarity:
        rel = rel_type.lower()
        if any(x in rel for x in ["increase", "activate", "upregulate", "positive"]):
            return Polarity.POSITIVE
        if any(x in rel for x in ["decrease", "inhibit", "downregulate", "negative"]):
            return Polarity.NEGATIVE
        return Polarity.NEUTRAL

    def _normalize_stage(self, model: str) -> EvidenceLevel:
        m = model.lower()
        if "human" in m or "clinical" in m:
            return EvidenceLevel.CLINICAL
        if "animal" in m or "mouse" in m or "rat" in m or "in vivo" in m:
            return EvidenceLevel.IN_VIVO
        if "cell" in m or "in vitro" in m:
            return EvidenceLevel.IN_VITRO
        return EvidenceLevel.UNKNOWN

    def _compute_id(self) -> str:
        raw = f"{self.subj}|{self.obj}|{self.relation_type}|{self.polarity}|{self.evidence_level}"
        return hashlib.md5(raw.encode()).hexdigest()
