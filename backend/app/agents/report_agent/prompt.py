"""
Report Agent Prompts
Prompt templates for research feasibility report generation
"""

# System Prompt - Research Analysis Expert
SYSTEM_PROMPT = """당신은 생명과학 분야 연구 전문가이자 학술 논문 분석 전문가입니다.

역할:
- 제시된 연구주제의 학술적 타당성을 평가
- 관련 논문들을 종합하여 근거 기반 분석 제공
- 연구 가능성, 한계, 권장사항을 균형있게 제시

지침:
- 모든 답변은 한국어로 작성 (고유명사 및 전문 용어 제외)
- 논문과 데이터 기반의 객관적 분석
- 출처와 근거 명시
- 명확한 논리 전개
- 전문 용어는 한국어 설명 포함"""

# Main report generation template
REPORT_GENERATION_PROMPT = """
분석 대상 연구주제:
{research_topic}

연구 설명:
{research_description}

분석 초점:
{analysis_goal}

관련 논문 목록:
{documents}

위 정보를 바탕으로 다음 내용을 포함하는 연구 타당성 평가 보고서를 작성하세요:

**인용 규칙**: 
- 모든 주장과 데이터에 대해 [파일명] 형식으로 출처를 명시하세요
- 고유명사(브랜드명, 기술명 등)를 제외하고는 모든 내용을 한글로 작성하세요

1. **연구 타당성 평가**
   - 타당성 점수 (0-100)
   - 평가 근거
   - 주요 발견사항

2. **선행 연구 분석**
   - 현재까지의 연구 동향
   - 유사 연구 사례
   - 차별성 분석

3. **방법론적 가능성**
   - 제안된 연구 방법의 적절성
   - 기술적 타당성
   - 필요 자원 평가

4. **예상 문제점 및 해결책**
   - 주요 연구 장애물
   - 극복 방안
   - 대안 모색

5. **학술적 기여도**
   - 예상 학술 기여
   - 산업적 응용 가능성
   - 사회적 의미

6. **최종 권장사항**
   - 연구 진행 여부 판단
   - 필요한 보완사항
   - 협력 분야 제안
"""

# Evidence synthesis template
EVIDENCE_SYNTHESIS_PROMPT = """
주어진 논문들을 분석하여 다음을 작성하세요:

1. 연구 주제와의 관련성
2. 각 논문의 핵심 발견
3. 논문들 간 연관관계
4. 종합적 결론

형식: 명확하고 간결하게"""

# Recommendation template
RECOMMENDATION_PROMPT = """
위 분석을 바탕으로 다음 연구자가 취할 수 있는 구체적인 행동 방안을 제시하세요:

1. 즉시 취할 수 있는 조치
2. 추가 검토 필요 사항
3. 협력 제안
4. 참고 자료 및 전문가"""

# Section headers
SECTION_TITLES = {
    "overview": "연구 개요 및 배경",
    "feasibility": "타당성 평가",
    "literature": "선행 연구 분석",
    "methodology": "방법론적 검토",
    "challenges": "예상 과제 및 해결방안",
    "contribution": "학술 기여도",
    "recommendations": "최종 권장사항"
}

# Configuration constants
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 6144  # Report는 더 긴 내용이 필요하므로 증가
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
MIN_MAX_TOKENS = 1000
MAX_MAX_TOKENS = 8192

# Report types
REPORT_TYPES = ["comprehensive", "summary", "detailed"]

# Feasibility thresholds
FEASIBILITY_THRESHOLDS = {
    "highly_feasible": 75,      # 75-100
    "feasible": 50,             # 50-74
    "uncertain": 25,            # 25-49
    "not_feasible": 0           # 0-24
}
