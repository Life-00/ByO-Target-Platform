from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
import hashlib
from enum import Enum

# Import ByO schemas (Input/Output interfaces)
from ...schemas.fact import Fact, FactSet
from ...schemas.claim import ValidatedClaims, ValidatedClaim, EvidenceItem, RiskSignal

# --- Internal Enums (Mirrored from PubMedQA/models.py for Logic) ---

class Polarity(int, Enum):
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1

class EvidenceLevel(str, Enum):
    IN_VITRO = "In Vitro"
    IN_VIVO = "In Vivo"
    CLINICAL = "Clinical"
    UNKNOWN = "Unknown"
    
    def __lt__(self, other):
        order = {self.UNKNOWN: 0, self.IN_VITRO: 1, self.IN_VIVO: 2, self.CLINICAL: 3}
        return order[self] < order[other]

class EdgeType(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONDITIONALLY_DIFFERENT = "CONDITIONALLY_DIFFERENT"

# --- Logic Layer ---

class CanonicalClaim:
    """
    Internal representation of a claim for graph building.
    Decoupled from the simple ByO 'Fact' schema to support complex validation logic.
    """
    def __init__(self, fact: Fact):
        self.original_fact = fact
        
        # 1. Normalize Subject/Object
        # Assumption: Subject is the first target, Object is from relation or derived
        self.subj = self._extract_subject(fact)
        self.obj = self._extract_object(fact)
        
        # 2. Normalize Relation & Polarity
        # ByO Fact.relation.type is distinct (increase, decrease, etc.)
        self.relation_type = fact.relation.type.lower()
        self.polarity = self._normalize_polarity(self.relation_type)
        
        # 3. Normalize Level
        self.evidence_level = self._normalize_stage(fact.experiment.model)
        
        # 4. Compute ID
        self.id = self._compute_id()

    @property
    def key_tuple(self):
        """Returns (Subject, Object, Relation) for grouping."""
        return (self.subj, self.obj, self.relation_type)

    def _extract_subject(self, fact: Fact) -> str:
        # Prefer target
        if fact.entities.target:
            return fact.entities.target[0].lower().strip()
        # Fallback
        if fact.entities.compound:
            return fact.entities.compound[0].lower().strip()
        return "unknown_subject"

    def _extract_object(self, fact: Fact) -> str:
        if fact.relation.object:
            return fact.relation.object.lower().strip()
        # Fallback if no explicit object in relation
        if fact.entities.disease:
             return fact.entities.disease[0].lower().strip()
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
        # Hash based on canonical content
        # bucket conditions (e.g. species) if necessary, for now keep simple
        raw = f"{self.subj}|{self.obj}|{self.relation_type}|{self.polarity}|{self.evidence_level}"
        return hashlib.md5(raw.encode()).hexdigest()


class ValidatorAgent:
    def __init__(self):
        self.risk_keywords = {
            "mobility": ["toxicity", "toxic", "adverse", "side effect", "poison"], # Mapped to 'toxicity' in schema? Schema says 'toxicity'
            "failure": ["fail", "no effect", "ineffective", "resistance"],
            "inconsistency": ["conflicting", "controversial"]
        }
        # Thresholds from root models
        self.similarity_threshold = 0.7 

    def process(self, fact_set: FactSet) -> ValidatedClaims:
        """
        Main entry point.
        Converts Facts -> CanonicalClaims -> Builds Graph/Clusters -> ValidatedClaims
        """
        # 1. Ingest & Normalize
        canonical_claims = [CanonicalClaim(f) for f in fact_set.facts]
        
        # 2. Cluster (Group by Subj-Obj-Rel)
        clusters = self._cluster_claims(canonical_claims)
        
        # 3. Generate ValidatedClaims from Clusters
        validated_list = []
        for key, group in clusters.items():
            validated_claim = self._synthesize_cluster(key, group)
            validated_list.append(validated_claim)
            
        return ValidatedClaims(claims=validated_list)

    def _cluster_claims(self, claims: List[CanonicalClaim]) -> Dict[tuple, List[CanonicalClaim]]:
        groups = defaultdict(list)
        for c in claims:
            # Grouping by semantic meaning
            groups[c.key_tuple].append(c)
        return groups

    def _synthesize_cluster(self, key: tuple, group: List[CanonicalClaim]) -> ValidatedClaim:
        subj, obj, rel = key
        
        # A. Analyze Consistency
        # Check if Polarity matches across the group
        polarities = {c.polarity for c in group}
        
        # If we have both Positive and Negative, it's conflicting
        if Polarity.POSITIVE in polarities and Polarity.NEGATIVE in polarities:
            consistency = "conflicting"
        # If only one type (ignoring Neutral maybe? or Neutral is separate)
        elif len(polarities) > 1:
            # e.g. Positive + Neutral -> Maybe consistent but weak?
            # For simplicity, if mixed non-conflicting, say 'consistent'
            consistency = "consistent"
        else:
            consistency = "consistent"
            
        # Determine strict contradiction if logic from root is needed
        # (Root logic checked similarity of conditions. Here we assume same key = same condition bucket for now)
        
        # B. Aggregate Evidence
        evidence_list = []
        evidence_counts = {"in_vitro": 0, "in_vivo": 0, "clinical": 0}
        
        for c in group:
            # Map canonical level to ByO string keys
            lvl_str = c.evidence_level.value.lower().replace(" ", "_")
            if lvl_str in evidence_counts:
                evidence_counts[lvl_str] += 1
                
            # Create EvidenceItem
            # Normalized level string for the item
            display_lvl = c.evidence_level.value.lower()
            ev_item = EvidenceItem(
                pmid=c.original_fact.pmid,
                sentence_id=c.original_fact.sentence_id,
                experiment_level=display_lvl
            )
            evidence_list.append(ev_item)

        # C. Detect Risks
        risk_signals = self._detect_risks(group)
        if risk_signals:
            # If risks found (e.g. toxicity), might override consistency or add flag
            if any(r.type == "failure" for r in risk_signals):
                if consistency == "consistent":
                    consistency = "insufficient" # or 'potential_failure'

        # D. Construct ValidatedClaim
        # Formulate a readable normalized claim string
        normalized_text = f"{subj} {rel} {obj}".strip()
        
        # Main ID from the first claim or a group hash
        # group[0].id is specific to that specific evidence combo.
        # We need a stable ID for the cluster.
        cluster_id = hashlib.md5(f"{subj}|{obj}|{rel}".encode()).hexdigest()

        return ValidatedClaim(
            claim_id=cluster_id,
            normalized_claim=normalized_text,
            evidence=evidence_list,
            evidence_summary=evidence_counts,
            consistency=consistency,
            risk_signals=risk_signals
        )

    def _detect_risks(self, group: List[CanonicalClaim]) -> List[RiskSignal]:
        signals = []
        seen_pmids = set()
        
        for c in group:
            text = c.original_fact.text.lower()
            
            for risk_type, keywords in self.risk_keywords.items():
                if any(k in text for k in keywords):
                    # Schema mapping: 'toxicity' | 'failure' | 'inconsistency'
                    # My keywords keys are mobility(?? -> toxicity), failure, etc.
                    
                    mapped_type = risk_type
                    if risk_type == "mobility": mapped_type = "toxicity" # fix key from init
                    
                    # Deduplicate by PMID per type
                    unique_key = (mapped_type, c.original_fact.pmid)
                    if unique_key in seen_pmids:
                        continue
                    seen_pmids.add(unique_key)
                    
                    signals.append(RiskSignal(
                        type=mapped_type,
                        pmid=c.original_fact.pmid,
                        sentence_id=c.original_fact.sentence_id
                    ))
        return signals
