# TVA - AI Research Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![FastAPI 0.109](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)

---

## 📋 프로젝트 개요

**TVA (Target Validation Assistant)**는 AI 에이전트 기반의 학술 연구 분석 플랫폼입니다.

**주요 기능:**
- 📚 PDF 문서 업로드 및 임베딩 (페이지 추적)
- 🔍 arXiv 논문 검색 및 자동 다운로드
- 💬 RAG 기반 문서 분석 (근거 제시)
- 🤖 4개 독립 AI Agent (General, Search, Embedding, Analysis)

---

## 🏗️ 프로젝트 구조

```
tva/
├── frontend/              # React + Vite (3-Panel UI)
├── backend/               # FastAPI + PostgreSQL + ChromaDB
│   └── app/agents/        # 모듈화된 AI Agent 시스템
└── Specification/         # 설계 문서
```

---

## ⚡ 빠른 시작

### 요구사항
- **Backend**: Python 3.12+, Docker, Docker Compose
- **Frontend**: Node.js 18+
- **API Key**: Upstage API Key (LLM + Embedding)

### 1. 백엔드 실행

```bash
cd backend

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 UPSTAGE_API_KEY 설정

# Docker로 실행 (PostgreSQL + ChromaDB + FastAPI)
docker-compose up -d

# 로그 확인
docker-compose logs -f backend
```

**백엔드 접속:**
- API: http://127.0.0.1:8001
- Swagger UI: http://127.0.0.1:8001/docs

### 2. 프론트엔드 실행

```bash
cd frontend

# 패키지 설치
npm install

# 개발 서버 실행
npm run dev
```

**프론트엔드 접속:** http://127.0.0.1:5173

---

## 🤖 AI Agent 시스템

현재 **4개 독립 Agent**가 운영 중입니다. 각 Agent는 완전히 독립적이며, 표준화된 구조를 따릅니다.

### 1. GeneralChatAgent
**용도**: LLM 기반 일반 대화  
**특징**: 선택적 문서 컨텍스트 제공 (RAG)  
**API**: `/api/v1/agents/general/message`

### 2. SearchAgent
**용도**: arXiv 논문 검색 및 다운로드  
**특징**: LLM 기반 요청 개수 추출, 중복 제거, 관련성 필터링  
**API**: `/api/v1/agents/search`

### 3. EmbeddingAgent
**용도**: PDF 문서 처리 및 임베딩  
**특징**: 페이지 번호 추적, 토큰 기반 청킹, 자동 요약 생성  
**API**: `/api/v1/agents/embedding`

### 4. AnalysisAgent
**용도**: RAG 기반 문서 분석  
**특징**: Vector search + 근거 제시 (문서명, 페이지, 텍스트 발췌)  
**API**: `/api/v1/agents/analysis`

**자세한 내용:** [`backend/app/agents/README.md`](backend/app/agents/README.md)

---

## 🎨 Frontend 기능

### 3-Panel Workspace
- **Library Panel**: 문서 목록, 필터링, 업로드
- **PDF Viewer**: react-pdf 기반 문서 뷰어
- **Chat Panel**: 4가지 Agent 모드 전환

### Agent 모드
- **General**: 일반 대화 (선택적 문서 컨텍스트)
- **Search**: arXiv 논문 검색
- **Analysis**: 선택된 문서 RAG 분석 (근거 포함)
- **Report**: 준비 중

### 주요 기술
- React 18 + Vite
- Zustand (상태 관리)
- TailwindCSS (스타일링)
- React-PDF (PDF 렌더링)

**자세한 내용:** [`frontend/README.md`](frontend/README.md)

---

## 🗄️ 백엔드 아키텍처

### 기술 스택
- **Framework**: FastAPI (비동기)
- **Database**: PostgreSQL (문서 메타데이터, 청크, 채팅 기록)
- **Vector DB**: ChromaDB (임베딩 벡터)
- **LLM**: Upstage Solar-1-mini-chat
- **Embedding**: Upstage embedding-passage (4096-dim)

### 주요 컴포넌트
- **Agent 시스템**: 모듈화된 독립 Agent (BaseAgent 상속)
- **서비스 계층**: LLMService, EmbeddingService, ChatService
- **API 라우터**: `/api/v1/agents/*`, `/api/v1/documents`, `/api/v1/sessions`
- **인증**: JWT 기반 (준비 완료)

**자세한 내용:** [`backend/README.md`](backend/README.md)

---

## 📊 데이터 흐름

### 1. 문서 업로드 → 임베딩
```
사용자 → PDF 업로드
       → EmbeddingAgent 실행
       → 페이지별 텍스트 추출
       → 토큰 기반 청킹 (2800 토큰, 오버랩 150)
       → 임베딩 생성 (Upstage)
       → PostgreSQL (청크 + 페이지 번호)
       → ChromaDB (벡터)
```

### 2. 논문 검색
```
사용자 → 검색 쿼리
       → SearchAgent 실행
       → LLM이 요청 개수 추출
       → arXiv API 호출
       → 관련성 필터링
       → PDF 다운로드 (/uploads/{session_id}/)
       → DB 등록 (is_indexed=False)
```

### 3. 문서 분석
```
사용자 → 질문 + 문서 선택
       → AnalysisAgent 실행
       → Vector search (ChromaDB, 상위 5개 청크)
       → 메타데이터 보강 (PostgreSQL, 페이지 번호)
       → LLM 답변 생성
       → 근거 추출 (문서명, p.X, 텍스트)
       → 응답 반환
```

---

## 🔧 개발 가이드

### 신규 Agent 개발
Agent 개발자를 위한 상세 가이드는 다음을 참조하세요:
- **Agent 개발 표준**: [`backend/app/agents/README.md`](backend/app/agents/README.md)
- **필수 구조**: `agent.py`, `schemas.py`, `prompt.py`
- **BaseAgent 상속**: `async execute(request) -> response`

### API 테스트
```bash
# Swagger UI
http://127.0.0.1:8001/docs

# 건강 체크
curl http://127.0.0.1:8001/api/v1/health
```

---

## 📝 로드맵

### ✅ 완료
- [x] 프론트엔드 3-Panel UI
- [x] 백엔드 Agent 시스템 (4개)
- [x] PDF 임베딩 (페이지 추적)
- [x] arXiv 검색
- [x] RAG 문서 분석 (근거 제시)
- [x] 채팅 히스토리 (모든 Agent 독립)

### 🔨 진행 중
- [ ] ChromaDB numpy 호환성 해결
- [ ] Analysis Agent 프론트엔드 UI 개선
- [ ] PDF 텍스트 하이라이트 기능

### 📅 예정
- [ ] Report Agent (자동 보고서 생성)
- [ ] PubMed 통합
- [ ] 다국어 지원
- [ ] 사용자 관리 (초대, 권한)

---

## 📄 라이선스

MIT License

---

## 👥 기여

프로젝트 구조와 표준을 준수하여 기여해주세요:
1. Agent 개발: [`backend/app/agents/README.md`](backend/app/agents/README.md) 참조
2. Frontend 컴포넌트: [`frontend/README.md`](frontend/README.md) 참조
3. Pull Request 시 변경사항 명확히 기술

---

## 📞 문의

프로젝트 관련 문의는 Issue를 생성해주세요.
  - React.memo & useMemo
  - Code splitting with React Router

### 기술 스택
```json
{
  "framework": "React 19.2.3",
  "bundler": "Vite 7.3.1",
  "styling": "TailwindCSS v4",
  "state": "Zustand",
  "routing": "React Router v6",
  "virtualization": "TanStack React Virtual"
}
```

### 실행 방법
```bash
cd frontend
npm install
npm run dev
# http://localhost:5173
```

---

## 🚀 Backend (Phase 1: 프로젝트 초기화 완료)

### 완성된 Phase 1
- ✅ 프로젝트 폴더 구조 생성
- ✅ UV 패키지 매니저 설정 (pyproject.toml)
- ✅ Docker + Docker Compose 구성
- ✅ FastAPI 기본 설정
- ✅ 중앙화된 LLM 프롬프트 관리 시스템
- ✅ Environment 설정 자동화

### 4가지 AI Agent 설계

#### 1️⃣ Search Indexer (논문 검색)
- arXiv API 통합
- PubMed Central API 통합
- 논문 메타데이터 추출
- 유사도 기반 랭킹

#### 2️⃣ PDF Analyzer (문서 분석)
- PDF 텍스트 추출
- 의미 기반 청킹 (512 토큰)
- Upstage Embedding API
- ChromaDB 자동 임베딩

#### 3️⃣ RAG Agent (질의응답)
- 의미론적 검색
- LLM 기반 답변 생성
- 자동 인용 생성
- Few-shot 프롬프팅

#### 4️⃣ Report Writer (보고서 생성)
- 자동 Literature Review
- Gap Analysis
- Feasibility Assessment
- 학술 양식 준수

### 중앙화된 LLM 설정

모든 Agent의 프롬프트, 페르소나, Few-shot 예제를 한 곳에서 관리:

```
app/config/
├── settings.py           # 환경 변수 & LLM 설정
├── llm_prompts.py       # ✨ 프롬프트 + 페르소나 + Few-shot
└── __init__.py
```

**장점:**
- 🔄 프롬프트 수정 시 모든 Agent에 자동 반영
- 📚 페르소나/Few-shot을 한 파일에서 관리
- 🧪 A/B 테스트 용이
- 📊 성능 추적 용이

### 데이터베이스 설계

#### PostgreSQL (9개 정규화 테이블)
- **users**: 사용자 계정
- **sessions**: 연구 세션
- **documents**: PDF 메타데이터
- **document_annotations**: 분석 결과
- **chat_messages**: Q&A 기록
- **analysis_reports**: 생성된 보고서
- **agent_logs**: Agent 실행 추적
- **api_usage**: API 사용량 추적
- **migrations**: 스키마 버전 관리

#### ChromaDB (단일 컬렉션)
- **documents_chunks**: 모든 문서 임베딩
  - 메타데이터 필터링 (session_id, document_id, source_section)
  - 의미론적 검색 지원

### 기술 스택

```json
{
  "framework": "FastAPI 0.109.0",
  "database": "PostgreSQL 16",
  "vectordb": "ChromaDB 0.4.18",
  "orm": "SQLAlchemy 2.0.23",
  "llm": "Upstage API",
  "packageManager": "UV",
  "python": "3.12+",
  "deployment": "Docker + Docker Compose"
}
```

### 폴더 구조

```
backend/
├── .env                  # 환경 변수
├── docker-compose.yml    # 3개 서비스 (PostgreSQL, ChromaDB, Redis)
├── Dockerfile
├── pyproject.toml        # UV 패키지 설정
├── README.md
│
├── app/
│   ├── config/           # ✨ 중앙 설정
│   │   ├── settings.py
│   │   └── llm_prompts.py
│   ├── main.py          # FastAPI 앱
│   ├── db/              # ORM & 마이그레이션
│   ├── services/        # 비즈니스 로직
│   ├── agents/          # 4개 독립 Agent
│   │   ├── search_indexer/
│   │   ├── pdf_analyzer/
│   │   ├── rag_agent/
│   │   ├── report_writer/
│   │   └── common/      # 공용 유틸리티
│   └── api/v1/          # API 라우터
│
└── tests/               # 테스트 스위트
```

### 실행 방법

#### 로컬 개발
```bash
cd backend

# 1. 환경 변수 설정
cp .env.example .env
# .env 파일에서 UPSTAGE_API_KEY 입력

# 2. 의존성 설치
pip install uv  # UV 설치 (처음 1회)
uv pip install -e .

# 3. FastAPI 서버 실행
uvicorn app.main:app --reload
# http://localhost:8000/docs
```

#### Docker (권장)
```bash
cd backend

# 1. 환경 변수 설정
cp .env.example .env

# 2. 서비스 실행
docker-compose up -d

# 3. 로그 확인
docker-compose logs -f backend

# 접속 주소
# API: http://localhost:8001
# Docs: http://localhost:8001/docs
```

---

## 📚 설계 문서

### Specification 폴더
```
Specification/
├── frontend_ROADMAP.md          # Frontend 로드맵 (✅ 완료)
├── backend_ROADMAP.md           # Backend 로드맵 (🔨 진행 중)
├── agent_list.md                # 4 Agent 상세 설계
├── db_postgresql.md             # PostgreSQL 설계
├── db_chromadb.md               # ChromaDB 설계
├── llm_config_management.md     # LLM 설정 시스템 설계
└── frontend.md                  # Frontend 기본 명세
```

### 문서 다운로드 경로
- [Frontend ROADMAP](/Specification/frontend_ROADMAP.md)
- [Backend ROADMAP](/Specification/backend_ROADMAP.md)
- [Agent 설계](/Specification/agent_list.md)
- [LLM 설정 관리](/Specification/llm_config_management.md)

---

## 🔄 프로젝트 진행 상황

### 완료 (✅)
- ✅ Frontend Phase 1-4 (100%)
- ✅ 전체 설계 문서
- ✅ Backend Phase 1 (프로젝트 초기화)

### 진행 중 (🔨)
- 🔨 Backend Phase 2 (PostgreSQL ORM 모델)
- 🔨 Backend Phase 3 (Agent 1: Search Indexer)

### 예정 (📋)
- 📋 Backend Phase 4 (Agent 2: PDF Analyzer)
- 📋 Backend Phase 5 (Agent 3: RAG Agent)
- 📋 Backend Phase 6 (Agent 4: Report Writer)
- 📋 Frontend-Backend 통합
- 📋 Docker 배포 최적화

---

## 🛠️ 개발 환경 설정

### 필수 요구사항
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- Upstage API Key (https://console.upstage.ai/)

### 로컬 개발 셋업

```bash
# 1. 저장소 클론
git clone <repo>
cd tva

# 2. Frontend 설정
cd frontend
npm install
npm run dev  # http://localhost:5173

# 3. Backend 설정 (다른 터미널)
cd backend
cp .env.example .env
# .env에서 UPSTAGE_API_KEY 설정
docker-compose up -d
# 또는 로컬: uv pip install -e . && uvicorn app.main:app --reload

# 4. 다 함께 실행
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000 (로컬) 또는 :8001 (Docker)
# Docs: http://localhost:8000/docs
```

---

## 📊 기술 선택 이유

### Frontend
- **React 19**: 최신 기능, 성능 최적화
- **Vite**: 빠른 개발 경험
- **TailwindCSS**: 유지보수 가능한 스타일
- **Zustand**: 간단한 상태 관리

### Backend
- **FastAPI**: 비동기, 자동 문서화, 타입 검증
- **SQLAlchemy**: 강력한 ORM, 마이그레이션
- **ChromaDB**: 간단한 벡터 DB, 메타데이터 필터링
- **Upstage API**: 한국어 최적화, 안정적 서비스
- **UV**: 빠른 패키지 설치, 결정적 lockfile

### Database
- **PostgreSQL**: 안정성, 확장성, JSON 지원
- **ChromaDB**: 의미론적 검색, 메타데이터 관리

---

## 🎯 핵심 기능

### 1. 의미론적 검색
- 사용자 쿼리를 임베딩
- ChromaDB에서 유사 청크 검색
- 페이지/섹션 참조 제공

### 2. 자동 보고서 생성
- 선택된 문서 분석
- Literature Review 자동 작성
- Gap Analysis & Feasibility Assessment
- 학술 양식 준수

### 3. 다중 출처 지원
- 로컬 PDF 업로드
- arXiv 논문 검색
- PubMed Central 논문 검색

### 4. Agent 추적
- 각 Agent의 실행 로그
- API 사용량 통계
- 실행 시간 측정

---

## 📈 성능 목표

| 메트릭 | 목표 |
|--------|------|
| Frontend FCP | < 1s |
| API 응답 | < 500ms |
| PDF 분석 (10개) | < 45s |
| 보고서 생성 | < 60s |
| 동시 사용자 | 100+ |

---

## 🔒 보안 고려사항

- ✅ JWT 기반 인증
- ✅ HTTPS 준비 (배포 시)
- ✅ CORS 설정
- ✅ Rate limiting (향후)
- ✅ API key 보안 (환경변수)

---

## 📝 라이선스

MIT License - 자유롭게 사용하세요.

---

## 👥 기여

TVA는 학술 연구를 위한 오픈소스 프로젝트입니다.
기여는 언제든 환영합니다!

---

## 📞 연락처

- 📧 이메일: [프로젝트 연락처]
- 🐛 이슈: [GitHub Issues]

---

## 🗺️ 로드맵

### 2026 Q1
- ✅ Frontend 완성
- ✅ Backend Phase 1
- 🔨 Backend Phase 2-4

### 2026 Q2
- 🔨 Backend Phase 5-6
- 📋 통합 테스트
- 📋 성능 최적화

### 2026 Q3
- 📋 프로덕션 배포
- 📋 모니터링 & 로깅
- 📋 추가 기능 (Webhooks, API 확장)

---

**마지막 업데이트**: 2026-01-17  
**상태**: 🟡 진행 중  
**Frontend**: ✅ 완료 | **Backend**: 🔨 진행 중 | **배포**: 📋 예정

---

Made with ❤️ for Academic Research
