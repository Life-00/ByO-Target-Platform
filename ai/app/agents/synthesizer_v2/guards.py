from typing import List
from app.schemas.vector_hit import VectorHit

class GuardError(ValueError):
    pass

def validate_hits(hits: List[VectorHit]) -> None:
    if not hits:
        raise GuardError("No vector hits provided")

    for h in hits:
        if not h.claim_text.strip():
            raise GuardError(f"Empty claim_text: {h.claim_id}")

        if not h.evidence:
            raise GuardError(f"Missing evidence: {h.claim_id}")

        for c in h.evidence:
            if not c.quote.strip():
                raise GuardError(f"Empty evidence quote: {h.claim_id}")
            if not c.pmid.strip() or not c.url.strip():
                raise GuardError(f"Missing citation fields: {h.claim_id}")

        for r in h.risk_signals:
            cit = r.citation
            if not cit.quote.strip() or not cit.pmid.strip() or not cit.url.strip():
                raise GuardError(f"Risk signal without citation: {h.claim_id}")
