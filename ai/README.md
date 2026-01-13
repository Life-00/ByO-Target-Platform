# 1. 전체 구조 개요
```text
ai/
├─ app/
│  ├─ core/                               # 공통 인프라
│  │   ├─ llm.py                         # LLM client / retry / logging
│  │   ├─ embeddings.py             # embedding 모델
│  │   ├─ vectordb.py                 # ChromaDB wrapper (add/search/filter)
│  │   └─ observability.py             # LangSmith, tracing
│  │
│  ├─ agents/                   
│  │   ├─ retriever/                   # RetrieverAgent
│  │   │   ├─              
│  │   │
│  │   ├─ extractor/                  # ExtractorAgent
│  │   │   ├─              
│  │   │
│  │   └─ synthesizer/               # SynthesizerAgent
│  │         ├─             
│  │
│  ├─ schemas/                        # 스키마 고정 (이미 합의됨)
│  │   ├─ api.py
│  │   ├─ query.py
│  │   ├─ retrieval.py
│  │   ├─ knowledge.py
│  │   ├─ report.py
│  │   └─ deprecated.py
│  │
│  ├─ services/                        # 외부 데이터 접근
│  │   └─ pubmed/
│  │       ├─ client.py
│  │       ├─ parser.py
│  │       └─ service.py
│  │
│  ├─ config/
│  │   └─ env.py
│  │
│  ├─ tests/
│  │
│  └─ main.py                      # FastAPI app
│
├─ main.py                           # 실행 entrypoint
├─ .env
├─ .gitignore
├─ pyproject.toml
├─ uv.lock
└─ README.md
```

---
# 2. 각 Agent 역할 정리
## 🔍 RetrieverAgent (논문 선별 에이전트)
### 역할 :
* 사용자 질의에 대해 관련성 있는 논문만 선별
* 초록(Abstract) 수준에서 keep / discard 판단
### 입력 :
* UserQuery
* PubMed 검색 결과 (PaperCorpus)
### 출력 :
* FilteredPaperCorpus
     - pmid
     - relevance score 
     - 선택 사유 (짧은 reasoning)
### 하지 않는 일 :
* 요약
* 지식 생성
* Vector DB 저장

## 🧪 ExtractorAgent (사실 구조화 에이전트)
### 역할 :
* 선별된 논문에서 KnowledgeChunk 생성
* 논문 -> RAG 가능한 의미 단위 지식으로 변환
### 입력 :
* Paper (abstract 또는 full text)
* UserQuery (컨텍스트)
### 출력 :
* KnowledgeDocument
     - 여러 개의 KnowledgeChunk
### 특징 :
* 반복 처리
* 부분 실패 허용
* 중간 결과 누적 
* LangGraph 사용 가능 (이 에이전트 내부에서만)

### 저장 :
* KnowledgeChunk 단위로 Vector DB에 즉시 저장

## 🧩 SynthesizerAgent (추론, 보고서 생성 에이전트)
### 역할 :
* Vector DB에 저장된 지식을 검색 
* 사용자 질의에 맞게 논리적 종합 + 보고서 생성
### 입력 :
* UserQuery
* KnowledgeChunk[] (Vector DB retrieval 결과)
### 출력 :
* SynthesizedReport
### 하지 않는 일 :
* write Vector DB
* 논문 해석

=> VectorDB에 저장된 지식들을 종합해 연구 답변을 작성
---
# 3. 에이전트 간 책임 경계
```text
RetrieverAgent
  └─ 논문 선별까지만

ExtractorAgent
  └─ 지식 생성까지만

SynthesizerAgent
  └─ 추론·서술까지만
```
# 4. 도식화
```text
┌────────────────────┐
│   User / Client    │
└─────────┬──────────┘
          │ UserQuery
          ▼
┌────────────────────┐
│  RetrieverAgent    │
│  - abstract filter │
│  - relevance score │
└─────────┬──────────┘
          │ Filtered Papers
          ▼
┌────────────────────────────┐
│  ExtractorAgent            │
│  (LangGraph optional)      │
│  - iterate sentences       │
│  - extract claims          │
│  - build KnowledgeChunks   │
└─────────┬──────────────────┘
          │ KnowledgeChunks
          ▼
┌────────────────────┐
│     Vector DB      │
│      (Chroma)      │
└─────────┬──────────┘
          │ Retrieved Chunks
          ▼
┌────────────────────┐
│  SynthesizerAgent  │
│  - reasoning       │
│  - ranking         │
│  - report writing  │
└─────────┬──────────┘
          │ SynthesizedReport
          ▼
┌────────────────────┐
│   User / Client    │
└────────────────────┘
```