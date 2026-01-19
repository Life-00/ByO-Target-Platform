# app/agents/synthesizer/agent.py
from typing import List

from app.schemas.vector_hit import VectorHit
from app.schemas.dossier import TargetDossier

from .guards import validate_hits
from .assembler import build_dossier_sections
from .post_validate import post_validate_dossier


class SynthesizerAgentV2:
    """
    지식 조각들을 모아 최종 연구 보고서를 생성하는 에이전트입니다.
    (Report Agent급 보장: assembler 결과를 post-validate로 후검증)
    """

    def run(self, user_query: str, hits: List[VectorHit], user_context: str = "") -> TargetDossier:
        # 1) 입력 데이터 검증 (필수 필드 확인)
        print(f"[Synthesizer] Running validation for {len(hits)} hits...")
        validate_hits(hits)

        # 2) 보고서 섹션 조립
        print("[Synthesizer] Assembling dossier sections...")
        dossier = build_dossier_sections(
            user_query=user_query,
            hits=hits,
            user_context=user_context,
        )

        # 3) Report-grade 후검증 (Evidence 포맷/섹션 키/최소 텍스트 보장)
        print("[Synthesizer] Post-validating dossier...")
        post_validate_dossier(dossier)

        return dossier
