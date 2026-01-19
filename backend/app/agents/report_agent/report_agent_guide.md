# 연구주제 타당성 평가 보고서 에이전트 (Report Agent)

## 📋 개요

바이오 연구자를 위한 논문 리서치 및 분석 자료를 종합하여, 최종 연구주제의 타당성을 평가하는 에이전트입니다.

**핵심 기능:**

- ✅ 연구주제의 학술적 타당성 평가
- ✅ 관련 논문 종합 분석 및 증거 도출
- ✅ 구조화된 연구 타당성 보고서 생성
- ✅ 시각화 및 네트워크 그래프 제공
- ✅ 권장사항 및 한계점 제시

---

## 🔧 기술 스택

### 필수 라이브러리

```
Core:
- pydantic (입출력 스키마)
- sqlalchemy + asyncpg (DB 연동)
- httpx (LLM API 호출)

Data Processing:
- pandas (표/데이터 정리)
- pint (단위 변환)

Report & Export:
- python-docx (DOCX 생성)
- reportlab (PDF 생성)

Visualization:
- plotly (웹 친화적 시각화)
- networkx + pyvis (증거 네트워크 그래프)

PDF Processing:
- PyMuPDF (fitz) (텍스트/좌표 추출)
- pdfplumber (필요시 추가)
```

---

## 🏗️ 모듈 구조

```
app/agents/report_agent/
├── __init__.py              # 패키지 export
├── agent.py                 # ReportAgent 클래스
├── schemas.py               # Pydantic 스키마
├── prompt.py                # LLM 프롬프트
├── tools.py                 # ✨ 유틸리티 tools 모음
├── report_builder.py        # ✨ 보고서 생성 로직
├── visualizer.py            # ✨ 시각화 엔진
└── report_agent_guide.md    # 이 문서
```

---

## 📦 핵심 Tool 정의

### 1️⃣ **DocumentProcessor Tool**

PDF/텍스트 문서 처리

```python
# tools.py
class DocumentProcessor:
    """문서 처리 도구"""

    async def extract_text(self, file_path: str) -> str:
        """PyMuPDF로 PDF 텍스트 추출"""

    async def extract_tables(self, file_path: str) -> List[pd.DataFrame]:
        """표 추출 및 pandas DataFrame 변환"""

    async def extract_metadata(self, file_path: str) -> Dict:
        """메타데이터: 저자, 연도, DOI 등"""
```

### 2️⃣ **DataNormalizer Tool**

데이터 정규화 및 단위 변환

```python
# tools.py
class DataNormalizer:
    """데이터 정규화 도구"""

    async def normalize_units(self, data: Dict, from_unit: str, to_unit: str) -> Dict:
        """pint를 사용한 단위 변환"""

    async def standardize_table(self, df: pd.DataFrame) -> pd.DataFrame:
        """표 데이터 정규화"""

    async def handle_unit_mismatch(self, data: Dict) -> Dict:
        """변환 불가 단위 처리 규칙"""
```

### 3️⃣ **ReportBuilder Tool**

구조화된 보고서 생성

```python
# report_builder.py
class ReportBuilder:
    """보고서 구성 도구"""

    async def build_markdown(self, report: ResearchReport) -> str:
        """Markdown 형식 보고서"""

    async def build_docx(self, report: ResearchReport, file_path: str) -> bytes:
        """DOCX 파일 생성 (python-docx)"""

    async def build_pdf(self, report: ResearchReport, file_path: str) -> bytes:
        """PDF 파일 생성 (reportlab)"""
```

### 4️⃣ **Visualizer Tool**

시각화 및 네트워크 그래프

```python
# visualizer.py
class Visualizer:
    """시각화 도구"""

    async def create_evidence_network(
        self,
        report: ResearchReport
    ) -> str:
        """networkx + pyvis로 증거 네트워크 그래프 생성

        Returns: HTML 형식 그래프
        """

    async def create_feasibility_chart(
        self,
        score: float,
        breakdown: Dict
    ) -> str:
        """타당성 점수 시각화 (plotly)"""

    async def create_trend_chart(
        self,
        data: List[Dict]
    ) -> str:
        """연구 동향 차트 (plotly)"""
```

### 5️⃣ **LLMIntegration Tool**

LLM 호출 및 응답 처리

```python
# tools.py
class LLMIntegration:
    """LLM 통합 도구"""

    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """LLMService 래퍼"""

    async def parse_validation(self, response: str) -> ResearchValidation:
        """LLM 응답에서 타당성 데이터 파싱"""

    async def extract_recommendations(self, response: str) -> List[str]:
        """LLM 응답에서 권장사항 추출"""
```

---

## 🔄 Chat Service와의 통합

`chat_service.py`와 동일한 패턴으로 모듈화:

### ReportService (제안)

```python
# app/services/report_service.py
class ReportService:
    """Report Agent 통합 서비스"""

    @staticmethod
    async def generate_report(
        session: AsyncSession,
        user_id: str,
        session_id: int,
        research_topic: str,
        research_data: ResearchTopicData,
        report_type: str = "comprehensive",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> dict:
        """
        Args:
            session: DB 세션
            user_id: 사용자 ID
            session_id: 채팅 세션 ID
            research_topic: 연구주제
            research_data: 문서 및 메타데이터
            report_type: 보고서 유형
            temperature: LLM 온도
            max_tokens: 최대 토큰

        Returns:
            {
                "report": ResearchReport,
                "report_html": str,
                "network_graph": str,
                "files": {"docx": bytes, "pdf": bytes},
                "generated_at": datetime
            }
        """
        # 1. 세션 검증 (ChatService와 동일)
        # 2. DocumentProcessor로 문서 처리
        # 3. ReportAgent.execute() 호출
        # 4. ReportBuilder로 포맷 생성
        # 5. Visualizer로 그래프 생성
        # 6. 결과 저장 및 반환
```

---

## 🚀 API 라우터 예상 구조

```python
# app/api/v1/agents/report.py
from fastapi import APIRouter

router = APIRouter(prefix="/report", tags=["agents"])

@router.post("/generate")
async def generate_report(
    request: ReportAgentRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReportAgentResponse:
    """연구 타당성 보고서 생성"""
    return await ReportService.generate_report(
        session=db,
        user_id=current_user["user_id"],
        session_id=request.session_id,
        research_topic=request.research_topic,
        research_data=request.research_data,
    )

@router.get("/export/{report_id}")
async def export_report(
    report_id: str,
    format: str = "docx",  # json, markdown, docx, pdf
) -> FileResponse:
    """생성된 보고서 내보내기"""
    # 저장된 보고서를 지정된 형식으로 변환
```

---

## 🎯 프론트엔드 연결 방식

```javascript
// 채팅 모드 선택
const chatModes = [
  { id: "general", label: "일반 대화", icon: "chat" },
  { id: "report", label: "타당성 보고서", icon: "report" },
  { id: "analysis", label: "논문 분석", icon: "analysis" },
];

// Report 모드 선택 시
async function generateReport() {
  const response = await fetch("/api/v1/agents/report/generate", {
    method: "POST",
    body: JSON.stringify({
      session_id: currentSessionId,
      research_topic: userInput,
      research_data: {
        topic: userInput,
        related_documents: selectedDocuments,
        analysis_goal: userGoal,
      },
      report_type: "comprehensive",
      include_visualizations: true,
      include_network_graph: true,
    }),
  });

  const result = await response.json();

  // 탭별 표시
  showReportTabs({
    summary: result.report, // JSON 요약
    html: result.report_html, // HTML 렌더링
    graph: result.network_graph, // 네트워크 그래프
    export: result.files, // DOCX/PDF 다운로드
  });
}
```

---

## 🔌 필수 환경 설정

`.env` 파일:

```env
# Report Agent
REPORT_ENABLE_PDF_EXPORT=true
REPORT_ENABLE_VISUALIZATION=true
REPORT_NETWORK_GRAPH_TYPE=pyvis  # pyvis or reactflow

# Visualization
PLOTLY_THEME=plotly_dark

# PDF Export
PDF_FONT_FAMILY=NotoSansCJK
```

---

## 🤖 Agent의 자동 Tool 선택 메커니즘

### 문제: 사용자 입력에 따른 동적 Tool 실행

사용자는 다양한 의도로 Report Agent를 사용합니다:

- "이 연구주제가 가능해?" → **전체 보고서 생성**
- "이 데이터를 정리해줘" → **DataNormalizer만 실행**
- "네트워크 그래프 만들어줘" → **Visualizer만 실행**
- "보고서를 PDF로 내보내줘" → **ReportBuilder만 실행**

**문제**: 모든 Tool을 매번 실행할 수 없음 (시간, 비용, 불필요)  
**해결책**: Agent가 의도(Intent)를 파악하고 필요한 Tool만 선택 실행

---

### Step 1️⃣: Intent 분류

```python
# agent.py
from enum import Enum

class ExecutionIntent(Enum):
    """사용자 의도 분류"""
    FULL_REPORT = "full_report"          # 전체 보고서 생성
    DATA_PROCESSING = "data_processing"  # 데이터 정리/변환
    VISUALIZATION = "visualization"      # 시각화만
    EXPORT = "export"                    # 내보내기만
    QUICK_ANALYSIS = "quick_analysis"    # 빠른 LLM 분석만
```

---

### Step 2️⃣: Intent 판단 로직

```python
# agent.py
class ReportAgent(BaseAgent):

    async def execute(self, request: ReportAgentRequest):
        # 1️⃣ Intent 분류
        intent = await self._classify_intent(request)
        logger.info(f"[ReportAgent] Intent: {intent.value}")

        # 2️⃣ Intent별 실행
        if intent == ExecutionIntent.FULL_REPORT:
            return await self._execute_full_report(request)
        elif intent == ExecutionIntent.DATA_PROCESSING:
            return await self._execute_data_processing(request)
        elif intent == ExecutionIntent.VISUALIZATION:
            return await self._execute_visualization(request)
        elif intent == ExecutionIntent.EXPORT:
            return await self._execute_export(request)
        else:
            return await self._execute_quick_analysis(request)

    async def _classify_intent(self, request: ReportAgentRequest) -> ExecutionIntent:
        """Intent 파악 (키워드 → 구조 → 기본값)"""

        # 1단계: 키워드 기반
        intent = self._keyword_based_intent(request.research_topic)
        if intent:
            return intent

        # 2단계: 요청 구조 기반
        if request.research_data and request.research_data.related_documents:
            return ExecutionIntent.FULL_REPORT
        elif hasattr(request, 'data_to_normalize') and request.data_to_normalize:
            return ExecutionIntent.DATA_PROCESSING
        elif hasattr(request, 'visualization_type') and request.visualization_type:
            return ExecutionIntent.VISUALIZATION
        elif hasattr(request, 'export_format') and request.export_format:
            return ExecutionIntent.EXPORT
        else:
            return ExecutionIntent.QUICK_ANALYSIS

    def _keyword_based_intent(self, text: str) -> Optional[ExecutionIntent]:
        """키워드 매칭으로 의도 판단"""
        keywords = {
            ExecutionIntent.DATA_PROCESSING: [
                '정리', '변환', '정규화', '단위', '표', '데이터', '통합'
            ],
            ExecutionIntent.VISUALIZATION: [
                '그래프', '차트', '시각화', '네트워크', '도식', '그림', '플롯'
            ],
            ExecutionIntent.EXPORT: [
                '내보내', '다운로드', '저장', '파일', 'pdf', 'docx', '다운'
            ],
            ExecutionIntent.QUICK_ANALYSIS: [
                '분석해줘', '평가해줘', '어때', '가능해', '어떻게', '의견'
            ],
            ExecutionIntent.FULL_REPORT: [
                '보고서', '타당성', '평가', '종합', '전체', '완전한'
            ]
        }

        text_lower = text.lower()
        for intent, kws in keywords.items():
            if any(kw in text_lower for kw in kws):
                return intent

        return None
```

---

### Step 3️⃣: Intent별 실행 함수

```python
# agent.py - 각 Intent별 처리

class ReportAgent(BaseAgent):

    async def _execute_full_report(self, request: ReportAgentRequest):
        """🔵 전체 보고서 생성
        실행: DocumentProcessor → DataNormalizer → LLM → ReportBuilder → Visualizer
        """
        documents_text = await DocumentProcessor.extract_text(...)
        normalized_data = await DataNormalizer.normalize_data(...)
        report_content = await self.llm_service.generate(prompt=...)
        report = await ReportBuilder.build_report(report_content)
        graphs = await Visualizer.create_network(report)

        return ReportAgentResponse(report=report, visualizations=graphs)

    async def _execute_data_processing(self, request: ReportAgentRequest):
        """🟢 데이터 정리만
        실행: DataNormalizer만
        """
        normalized = await DataNormalizer.normalize_units(
            data=request.data_to_normalize,
            unit_conversion=request.unit_conversion
        )

        return ReportAgentResponse(
            content="데이터 정리 완료",
            metadata={"normalized_data": normalized}
        )

    async def _execute_visualization(self, request: ReportAgentRequest):
        """🟡 시각화만
        실행: Visualizer만
        """
        graph = await Visualizer.create_visualization(
            data=request.visualization_data,
            viz_type=request.visualization_type
        )

        return ReportAgentResponse(content=graph)

    async def _execute_export(self, request: ReportAgentRequest):
        """🟠 내보내기만
        실행: ReportBuilder로 포맷 변환
        """
        if request.export_format == "docx":
            output = await ReportBuilder.build_docx(request.report_to_export)
        elif request.export_format == "pdf":
            output = await ReportBuilder.build_pdf(request.report_to_export)
        else:
            output = await ReportBuilder.build_markdown(request.report_to_export)

        return ReportAgentResponse(
            content="파일 생성 완료",
            metadata={"file": output}
        )

    async def _execute_quick_analysis(self, request: ReportAgentRequest):
        """⚪ 빠른 LLM 분석
        실행: LLM만 호출 (보고서 미생성)
        """
        analysis = await self.llm_service.generate(
            messages=[{"role": "user", "content": request.research_topic}],
            system_prompt=self.system_prompt
        )

        return ReportAgentResponse(content=analysis["content"])
```

---

### Step 4️⃣: 요청 스키마 확장

```python
# schemas.py
class ReportAgentRequest(BaseModel):
    """Intent에 따른 선택적 파라미터 포함"""

    # 기본 필수 정보
    research_topic: str = Field(..., description="연구 주제")
    research_data: Optional[ResearchTopicData] = None

    # Intent: FULL_REPORT (research_data 필수)
    report_type: str = Field(default="comprehensive")
    include_visualizations: bool = Field(default=True)

    # Intent: DATA_PROCESSING (data_to_normalize 필수)
    data_to_normalize: Optional[Dict] = None
    unit_conversion: Optional[Dict] = None  # {"from": "kg", "to": "mg"}

    # Intent: VISUALIZATION (visualization_type 필수)
    visualization_type: Optional[str] = None  # "network", "chart", "trend"
    visualization_data: Optional[List[Dict]] = None

    # Intent: EXPORT (export_format 필수)
    export_format: Optional[str] = None  # "docx", "pdf", "markdown"
    report_to_export: Optional[ResearchReport] = None

    # LLM 설정
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1000, le=8192)

    # 세션 정보
    session_id: Optional[int] = None
```

---

### Step 5️⃣: 프론트엔드 사용 예시

```javascript
// 📌 예시 1: 전체 보고서 생성
// research_data가 있으면 FULL_REPORT로 자동 인식
await api.post('/agents/report/generate', {
  research_topic: '암 면역치료의 효과',
  research_data: { related_documents: [...] },
  report_type: 'comprehensive'
});

// 📌 예시 2: 데이터 정리만
// data_to_normalize가 있으면 DATA_PROCESSING으로 자동 인식
await api.post('/agents/report/generate', {
  research_topic: '데이터 정리',
  data_to_normalize: { temp: '37도' },
  unit_conversion: { from: '℃', to: 'K' }
});

// 📌 예시 3: 그래프 생성
// visualization_type이 있으면 VISUALIZATION으로 자동 인식
await api.post('/agents/report/generate', {
  research_topic: '증거 네트워크',
  visualization_type: 'network',
  visualization_data: [...]
});

// 📌 예시 4: PDF 내보내기
// export_format이 있으면 EXPORT로 자동 인식
await api.post('/agents/report/generate', {
  research_topic: 'PDF 생성',
  export_format: 'pdf',
  report_to_export: { ... }
});

// 📌 예시 5: 빠른 분석 (선택적 파라미터 없음)
// QUICK_ANALYSIS로 자동 인식 (LLM만 호출)
await api.post('/agents/report/generate', {
  research_topic: '이 주제가 실현 가능해?'
});
```

---

### Tool 선택 플로우차트

```
사용자 입력
    ↓
[Intent 분류]
    ├─ 키워드 매칭? (정리/변환/그래프/내보내 등)
    │   └─ ✓ → Intent 결정
    │   └─ ✗ → 다음 단계
    ├─ 요청 구조 분석
    │   ├─ research_data + documents? → FULL_REPORT
    │   ├─ data_to_normalize? → DATA_PROCESSING
    │   ├─ visualization_type? → VISUALIZATION
    │   ├─ export_format? → EXPORT
    │   └─ 모두 없음? → QUICK_ANALYSIS
    ↓
[Intent별 Tool 실행]
    ├─ FULL_REPORT: 모든 Tool 순차 실행
    ├─ DATA_PROCESSING: DataNormalizer만
    ├─ VISUALIZATION: Visualizer만
    ├─ EXPORT: ReportBuilder만
    └─ QUICK_ANALYSIS: LLMService만
    ↓
응답 반환
```

---

## 📝 데이터 흐름

```
프론트엔드 (채팅 + Report 모드)
    ↓
API: POST /api/v1/agents/report/generate
    ↓
ReportService.generate_report()
    ├─ DocumentProcessor.extract_text()
    ├─ DataNormalizer.standardize_table()
    ├─ ReportAgent.execute()
    │  ├─ LLMIntegration.call_llm()
    │  ├─ parse_validation()
    │  └─ extract_recommendations()
    ├─ ReportBuilder.build_docx/pdf()
    ├─ Visualizer.create_evidence_network()
    └─ DB 저장
    ↓
응답: ReportAgentResponse
    ├─ report (JSON)
    ├─ report_html (Markdown)
    ├─ network_graph (HTML/JSON)
    └─ files (바이너리)
    ↓
프론트엔드 (다중 탭 표시 + 다운로드)
```

---

## ✅ 구현 체크리스트

- [ ] DocumentProcessor 구현
- [ ] DataNormalizer 구현
- [ ] ReportBuilder 구현
- [ ] Visualizer 구현
- [ ] ReportService 구현
- [ ] API 라우터 추가
- [ ] DB 모델 확장 (Report 저장용)
- [ ] 프론트엔드 통합
