# ai/app/agents/synthesizer_v2/agent.py
from typing import List
from app.schemas.vector_hit import VectorHit
from app.schemas.dossier import TargetDossier
from .guards import validate_hits
from .assembler import build_dossier_sections

class SynthesizerAgentV2:
    def run(self, user_query: str, hits: List[VectorHit], user_context: str = "") -> TargetDossier:
        # 1) 근거/출처 없는 입력은 여기서 차단
        validate_hits(hits)

        # 2) 고정 폼 섹션들 생성
        return build_dossier_sections(user_query=user_query, hits=hits, user_context=user_context)
