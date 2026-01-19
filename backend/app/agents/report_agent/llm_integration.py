"""
LLM Integration
LLM calling and response processing utilities
"""

import logging
import re
from typing import Optional, List

from app.services.llm_service import get_llm_service
from app.agents.report_agent.schemas import ResearchValidation

logger = logging.getLogger(__name__)


class LLMIntegration:
    """LLM 호출 및 응답 처리 도구"""

    def __init__(self):
        self.llm_service = get_llm_service()

    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        LLM 호출

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트
            temperature: 온도
            max_tokens: 최대 토큰

        Returns:
            LLM 응답
        """
        try:
            logger.info(f"[LLMIntegration] Calling LLM with prompt: {prompt[:50]}...")

            response = await self.llm_service.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response["content"]

        except Exception as e:
            logger.error(f"[LLMIntegration] Error calling LLM: {str(e)}")
            raise

    @staticmethod
    async def parse_validation(response: str) -> ResearchValidation:
        """
        LLM 응답에서 타당성 정보 파싱

        Args:
            response: LLM 응답

        Returns:
            ResearchValidation 객체
        """
        try:
            logger.info(f"[LLMIntegration] Parsing validation from response")

            # 점수 추출 (0-100)
            score_match = re.search(r"(?:점수|score)[:\s]*(\d+(?:\.\d+)?)", response, re.IGNORECASE)
            score = float(score_match.group(1)) if score_match else 75.0

            # 타당성 판단
            is_feasible = score >= 50

            # 추론 추출 (처음 500자)
            reasoning = response[:500] if response else "분석 결과를 확인하세요"

            return ResearchValidation(
                is_feasible=is_feasible,
                feasibility_score=min(100, max(0, score)),
                reasoning=reasoning
            )

        except Exception as e:
            logger.error(f"[LLMIntegration] Error parsing validation: {str(e)}")
            # 기본값 반환
            return ResearchValidation(
                is_feasible=True,
                feasibility_score=50.0,
                reasoning="타당성 분석 진행 중"
            )

    @staticmethod
    async def extract_recommendations(response: str) -> List[str]:
        """
        LLM 응답에서 권장사항 추출

        Args:
            response: LLM 응답

        Returns:
            권장사항 리스트
        """
        try:
            logger.info(f"[LLMIntegration] Extracting recommendations")

            recommendations = []

            # 패턴 1: 번호 목록 (1. 2. 3. ...)
            pattern1 = re.findall(r"\d+\.\s+([^\n]+)", response)
            if pattern1:
                recommendations.extend(pattern1)

            # 패턴 2: 하이픈 목록 (- ... )
            pattern2 = re.findall(r"-\s+([^\n]+)", response)
            if pattern2:
                recommendations.extend(pattern2)

            # 패턴 3: 권장사항 섹션
            if "권장사항" in response or "권고" in response:
                section_match = re.search(
                    r"(?:권장사항|권고)[^:]*:?\s*([^##]+?)(?:##|$)",
                    response,
                    re.IGNORECASE | re.DOTALL
                )
                if section_match:
                    section_text = section_match.group(1)
                    lines = [line.strip() for line in section_text.split("\n") if line.strip()]
                    recommendations.extend(lines[:10])  # 최대 10개

            # 기본값 (추천사항 없으면)
            if not recommendations:
                recommendations = [
                    "논문 리뷰를 통한 추가 선행 연구 검토",
                    "제시된 방법론의 현실성 검증",
                    "협력 기관 및 전문가 네트워크 구축"
                ]

            logger.info(f"[LLMIntegration] Extracted {len(recommendations)} recommendations")
            return recommendations[:10]  # 최대 10개

        except Exception as e:
            logger.error(f"[LLMIntegration] Error extracting recommendations: {str(e)}")
            return []

    @staticmethod
    async def extract_limitations(response: str) -> List[str]:
        """
        LLM 응답에서 한계점 추출

        Args:
            response: LLM 응답

        Returns:
            한계점 리스트
        """
        try:
            logger.info(f"[LLMIntegration] Extracting limitations")

            limitations = []

            # 패턴: 한계 섹션
            section_match = re.search(
                r"(?:한계|제한|한정|문제점)[^:]*:?\s*([^##]+?)(?:##|$)",
                response,
                re.IGNORECASE | re.DOTALL
            )

            if section_match:
                section_text = section_match.group(1)
                lines = [line.strip() for line in section_text.split("\n") if line.strip()]
                limitations.extend(lines[:10])

            # 기본값
            if not limitations:
                limitations = [
                    "분석 대상 논문의 제한된 수",
                    "특정 연구 분야에 편향될 수 있음",
                    "최신 연구 동향 반영 필요"
                ]

            logger.info(f"[LLMIntegration] Extracted {len(limitations)} limitations")
            return limitations[:10]

        except Exception as e:
            logger.error(f"[LLMIntegration] Error extracting limitations: {str(e)}")
            return []
