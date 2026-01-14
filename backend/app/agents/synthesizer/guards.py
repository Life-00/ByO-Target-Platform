# app/agents/synthesizer/guards.py
from typing import List
from app.schemas.vector_hit import VectorHit

class GuardError(ValueError): pass

def validate_hits(hits: List[VectorHit]) -> None:
    """
    근거 데이터가 보고서를 생성하기에 충분한지 검증합니다.
    """
    if not hits:
        raise GuardError("분석할 지식 정보가 없습니다. Extractor를 먼저 실행하세요.")

    for h in hits:
        if not h.claim_text.strip():
            raise GuardError(f"주장 내용이 비어 있습니다 (ID: {h.claim_id})")
        if not h.evidence:
            raise GuardError(f"근거 데이터가 없습니다 (ID: {h.claim_id})")
    
    print("[Guards] All hits validated successfully.")