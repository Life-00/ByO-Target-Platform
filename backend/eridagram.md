# 📊 TVA 데이터베이스 ERD

```
┌─────────────────────┐
│       users         │
│─────────────────────│
│ • id (PK)          │
│ • email (UK)       │
│ • username (UK)    │
│ • hashed_password  │
│ • is_active        │
│ • is_admin         │
│ • created_at       │
│ • updated_at       │
└─────────────────────┘
         │
         ├─────────────────────────────────┐
         │                                 │
         ↓                                 ↓
┌─────────────────────┐         ┌─────────────────────┐
│     sessions        │         │     documents       │
│─────────────────────│         │─────────────────────│
│ • id (PK)          │         │ • id (PK)          │
│ • user_id (FK)     │←────┐   │ • user_id (FK)     │
│ • title            │     │   │ • session_id (FK)  │
│ • description      │     │   │ • title            │
│ • analysis_goal    │     └───│ • description      │
│ • is_active        │         │ • file_name        │
│ • created_at       │         │ • file_path        │
│ • updated_at       │         │ • file_size        │
└─────────────────────┘         │ • page_count       │
         │                      │ • mime_type        │
         │                      │ • is_indexed       │
         ↓                      │ • indexed_at       │
┌─────────────────────┐         │ • keywords (JSON)  │
│  chat_messages      │         │ • sections (JSON)  │
│─────────────────────│         │ • extracted_abstract│
│ • id (PK)          │         │ • summary          │
│ • session_id (FK)  │         │ • relevance_score  │
│ • user_id (FK)     │         │ • source           │
│ • document_id (FK) │─────────│ • external_id      │
│ • role             │         │ • created_at       │
│ • content          │         │ • updated_at       │
│ • model_used       │         └─────────────────────┘
│ • tokens_used      │                  │
│ • created_at       │                  ├──────────────────────┐
└─────────────────────┘                  │                      │
         │                               ↓                      ↓
         │                      ┌─────────────────────┐ ┌─────────────────────┐
         │                      │  document_chunks    │ │ analysis_reports    │
         │                      │─────────────────────│ │─────────────────────│
         ↓                      │ • id (PK)          │ │ • id (PK)          │
┌─────────────────────┐         │ • document_id (FK) │ │ • document_id (FK) │
│  search_history     │         │ • chunk_index      │ │ • agent_type       │
│─────────────────────│         │ • page_number      │ │ • report_type      │
│ • id (PK)          │         │ • text_content     │ │ • title            │
│ • user_id (FK)     │         │ • char_count       │ │ • content          │
│ • session_id (FK)  │         │ • chroma_id (UK)   │ │ • meta_data        │
│ • query            │         │ • embedding_model  │ │ • is_public        │
│ • source           │         │ • created_at       │ │ • created_at       │
│ • papers_found     │         └─────────────────────┘ │ • updated_at       │
│ • papers_downloaded│                  │              └─────────────────────┘
│ • papers_filtered  │                  │
│ • min/max/avg_score│                  ↓
│ • search_time      │         ┌─────────────────────┐
│ • from_cache       │         │document_annotations │
│ • notes            │         │─────────────────────│
│ • created_at       │         │ • id (PK)          │
└─────────────────────┘         │ • document_id (FK) │
                                │ • user_id (FK)     │
┌─────────────────────┐         │ • page_number      │
│   search_cache      │         │ • highlight_text   │
│─────────────────────│         │ • note             │
│ • id (PK)          │         │ • annotation_type  │
│ • user_id (FK)     │         │ • created_at       │
│ • query_hash       │         │ • updated_at       │
│ • source           │         └─────────────────────┘
│ • papers_json      │
│ • result_count     │         ┌─────────────────────┐
│ • ttl_seconds      │         │    agent_logs       │
│ • created_at       │         │─────────────────────│
│ • expires_at       │         │ • id (PK)          │
│ • accessed_at      │         │ • agent_name       │
│ • access_count     │         │ • document_id (FK) │
└─────────────────────┘         │ • status           │
                                │ • input_data       │
┌─────────────────────┐         │ • output_data      │
│     api_usage       │         │ • error_message    │
│─────────────────────│         │ • execution_time_ms│
│ • id (PK)          │         │ • tokens_used      │
│ • user_id (FK)     │         │ • created_at       │
│ • endpoint         │         │ • updated_at       │
│ • method           │         └─────────────────────┘
│ • status_code      │
│ • response_time_ms │
│ • request/response │
│   size_bytes       │
│ • ip_address       │
│ • created_at       │
└─────────────────────┘
```

## 🔗 주요 관계(Relationships)

1. **users → sessions** (1:N) - 한 사용자가 여러 세션 생성
2. **users → documents** (1:N) - 한 사용자가 여러 문서 업로드
3. **users → chat_messages** (1:N) - 한 사용자가 여러 채팅 메시지
4. **sessions → chat_messages** (1:N) - 한 세션에 여러 채팅 메시지
5. **documents → document_chunks** (1:N) - 한 문서가 여러 청크로 분할
6. **documents → analysis_reports** (1:N) - 한 문서에 여러 분석 리포트
7. **documents → document_annotations** (1:N) - 한 문서에 여러 주석
8. **documents ← sessions** (N:1) - 세션에 문서 연결 (optional)

## 📋 테이블 분류

### Core Tables (핵심 테이블)
- **users** - 사용자 계정 및 인증
- **sessions** - 사용자 작업 세션 (워크스페이스)
- **documents** - 업로드된 PDF 문서
- **chat_messages** - 채팅 대화 기록

### Document Processing (문서 처리)
- **document_chunks** - 벡터 검색을 위한 문서 청크
- **analysis_reports** - AI가 생성한 분석 리포트
- **document_annotations** - 사용자 주석 및 하이라이트

### Search & Cache (검색 및 캐시)
- **search_cache** - 검색 결과 캐시 (TTL 7일)
- **search_history** - 사용자 검색 이력 추적

### Monitoring (모니터링)
- **agent_logs** - AI 에이전트 실행 로그
- **api_usage** - API 사용량 추적

## 📝 상세 테이블 설명

### users
사용자 계정 정보를 저장하는 핵심 테이블
- 이메일과 사용자명은 고유(UNIQUE) 제약조건
- 패스워드는 해시 처리되어 저장
- is_active, is_admin 플래그로 권한 관리

### sessions
사용자의 작업 세션(워크스페이스)을 관리
- 각 세션은 독립적인 채팅 및 문서 작업 공간
- analysis_goal: 사용자가 설정한 분석 목표

### documents
업로드된 PDF 문서의 메타데이터
- 파일 정보: 경로, 크기, 페이지 수, MIME 타입
- PDF 메타데이터: keywords, sections, extracted_abstract
- 관련성 점수(relevance_score): LLM이 평가한 0-1 점수
- source: arxiv, pubmed, manual_upload 등 출처

### document_chunks
문서를 작은 단위로 분할하여 저장
- 벡터 검색 및 RAG를 위한 텍스트 청크
- chroma_id: ChromaDB의 임베딩 ID
- embedding_model: 임베딩 생성에 사용된 모델

### chat_messages
사용자와 AI 간의 채팅 기록
- role: "user" 또는 "assistant"
- model_used: 사용된 LLM 모델
- tokens_used: 토큰 사용량 추적

### analysis_reports
AI 에이전트가 생성한 분석 리포트
- agent_type: search_indexer, pdf_analyzer, rag_agent, report_writer
- report_type: summary, analysis, extraction 등
- meta_data: JSON 형식의 분석 상세 정보

### document_annotations
사용자가 문서에 남긴 주석
- annotation_type: highlight, comment, bookmark 등
- page_number: 주석이 달린 페이지 번호

### search_cache
검색 결과를 캐시하여 성능 최적화
- query_hash: SHA-256으로 해시된 쿼리
- TTL 기본값 7일 (604800초)
- access_count: 캐시 히트 횟수

### search_history
사용자의 검색 이력 추적
- 검색 통계: papers_found, papers_filtered
- 관련성 점수 통계: min/max/avg_relevance_score
- 성능 지표: search_time_seconds, from_cache

### agent_logs
AI 에이전트 실행 로그
- status: pending, running, completed, failed
- execution_time_ms: 실행 시간 (밀리초)
- error_message: 실패 시 에러 메시지

### api_usage
API 사용량 모니터링
- endpoint, method, status_code
- 성능 지표: response_time_ms, request/response_size_bytes
- ip_address: 요청 IP 주소

## 🔍 인덱스 전략

주요 인덱스가 설정된 컬럼:
- 외래 키 (FK) 컬럼 전체
- 검색에 자주 사용되는 컬럼: email, username, created_at
- 고유 제약조건: email, username, chroma_id

## 🗑️ 삭제 정책 (Cascade)

- users 삭제 → sessions, documents, chat_messages 모두 삭제
- documents 삭제 → document_chunks, analysis_reports, annotations 모두 삭제
- sessions 삭제 → chat_messages 모두 삭제
- documents 삭제 → chat_messages의 document_id는 NULL로 설정 (SET NULL)
