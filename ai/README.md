# 1. 전체 구조 개요
```text
ai/
├─ app/
│  ├─ agents/
│  │  ├─ dialogue/                    # LangGraph 기반 중앙 에이전트
│  │  │  ├─ agent.py                  # DialogueAgent (parse → route → run)
│  │  │  └─ state.py                  # DialogueState
│  │  │
│  │  ├─ orchestrator/                # LangGraph 기반 파이프라인 제어
│  │  │  └─ agent.py                  # OrchestratorAgent
│  │  │
│  │  ├─ extractor/                   # LangGraph 기반 Extractor
│  │  │  ├─ agent.py                  # ExtractorAgent
│  │  │  ├─ graph.py                  # LangGraph 정의
│  │  │  ├─ state.py                  # ExtractorState
│  │  │  └─ nodes.py                  # iterate / entity / experiment / relation / assemble
│  │  │
│  │  ├─ retriever/                   # LangGraph 기반 Retriever
│  │  │  ├─ agent.py                  # RetrieverAgent
│  │  │  └─ state.py                  # RetrieverState 
│  │  │
│  │  ├─ validator/                   # LangGraph 기반 Validator
│  │  │  ├─ agent.py                  # ValidatorAgent
│  │  │  ├─ graph.py                  # LangGraph 정의
│  │  │  ├─ state.py                  # ValidatorState
│  │  │  └─ nodes.py                  # canonicalization / clustering / evidence aggregation / risk signal detection
│  │  │   
│  │  └─ synthesizer/
│  │      └─ agent.py                 # SynthesizerAgent                     
│  │
│  ├─ schemas/                        # 스키마 고정
│  │  ├─ user_query.py                # UserQuery, SearchConstraints
│  │  ├─ paper.py                     # Paper, PaperCorpus
│  │  ├─ fact.py                      # Fact, FactSet
│  │  ├─ claim.py                     # ValidatedClaim(s)
│  │  ├─ dossier.py                   # TargetDossier
│  │  └─ message.py                   # UserMessage, SystemResponse
│  │
│  ├─ services/
│  │  └─ pubmed/                      # Service layer (Agent 아님)
│  │     ├─ client.py                 # PubMed API 호출
│  │     ├─ parser.py                 # abstract → sentence 분해
│  │     └─ service.py                # search_pubmed()
│  │
│  ├─ config/
│  │  └─ env.py                       # api key 설정
│  │
│  ├─ tests/
│  │  └─ agents/                      # 각 agent 별로 테스트 진행
│  │      ├─ test_retriever_agent.py 
│  │      ├─ test_dialogue_flow.py
│  │      ├─ test_orchestrator_pipeline.py
│  │      ├─ test_extractor_agent.py
│  │      ├─ test_validator_agent.py
│  │      └─ test_synthesizer_agent.py
│  │ 
│  │                    
│  └─ main.py                         # 애플리케이션 main (run 함수)
│
├─ main.py                            # 실행용 entrypoint (wrapper)
├─ .env				                  # api key 등록 (형식은 .env_example 확인)
├─ .gitignore
├─ pyproject.toml
├─ uv.lock
└─ README.md
```

---
# 2. 각 Agent 역할 정리
## 🗣️ DialogueAgent (중앙 커뮤니케이션 에이전트)
### 역할 :
* 사용자 입력 해석
* 시스템 응답 생성
* 사용자와의 상호작용 관리
### 하지 않는 것 :
* PubMed 검색 ❌ 
* 논문 파싱 ❌ 
* 사실 판단 ❌
### 특징 :
* 중앙 진입점 
* LangGraph 기반 상태 관리 
* 필요 시 사용자에게 재질문 가능

## 🧭 OrchestratorAgent (흐름 제어 에이전트)
### 역할 :
* 전체 에이전트 흐름 제어
* 단계별 Agent 호출
* 상태 전이 관리
### 하지 않는 것 :
* 논문 검색 방법 결정 ❌ 
* 사실 추출 ❌
### 특징 :
* LangGraph 기반
* Retriever / Extractor / Validator 등을 연결
* 조건 분기 가능

## 🔍 RetrieverAgent (정보 수집 전략 에이전트)
### 역할 :
* 검색 전략 결정 
* 검색어 확장/축소 판단 
* 재검색 여부 판단
### 특징 :
* LangGraph 기반

## 🧪 ExtractorAgent (사실 추출 에이전트)
### 역할 :
* 논문 abstract로부터 사실(Fact) 추출 
* 문장 단위 정보 구조화
### 특징 :
* LangGraph 기반
* 현재는 rule-based, LLM으로 확장 예정
* ### 입력 : PaperCorpus
* ### 출력 : FactSet

## ⚖️ ValidatorAgent (근거 집계 에이전트)
### 역할 :
* 동일 주장 집계
* 근거 수 계산
* 상충 여부 표시
### 특징 :
* LangGraph 기반
* 판단 Agent ❌
* 집계/정리 전용

## 🧩 SynthesizerAgent (결과 구성 에이전트)
### 역할 :
* 최종 Dossier 구성
* 핵심 주장 요약
* 근거 수준 정리
### 특징 :
* LangGraph 기반
* 현재는 rule-based, LLM으로 확장 예정

```text
┌─────────────────────┐
│       사용자         │
│  (자연어 질문 입력)   │  
└───────────┬─────────┘
            ▼
┌───────────────────────┐
│     DialogueAgent     │
│ ① 입력 해석            │
│ ② 누락 정보 질문        │
│ ③ 사용자 선택 관리      │
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│   OrchestratorAgent   │
│ ④ 전체 흐름 판단        │
│ ⑤ Agent 호출 제어      │
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│   ExtractorAgent      │
│ ⑥ 논문 → Fact 추출     │
└───────────┬───────────┘
            ▼
┌────────────────────────┐
│   ValidatorAgent       │
│ ⑦ Claim 정규화         │
│ ⑧ 근거 일관성 평가       │
│ ⑨ Risk Signal 탐지     │
└───────────┬────────────┘
            ▼
┌───────────────────────┐
│   OrchestratorAgent   │
│ ⑩ 결과 해석            │
│ ⑪ 추가 검색 필요 판단   │
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│   SynthesizerAgent    │
│ ⑫ 결과 구성(보고서화)   │
│  - 핵심 주장 요약       │
│  - 근거 수준 정리       │
│  - Risk 정리           │
└───────────┬───────────┘
            ▼
┌───────────────────────┐
│   DialogueAgent       │
│ ⑬ 사용자에게 설명       │
│ ⑭ 추가 검색 여부 질문   │
└───────────┬───────────┘
            ▼
┌──────────────────────┐
│     최종 결과 전달     │
│   (또는 재검색 루프)   │
└──────────────────────┘
```
---
# 3. Agents 설계 원칙 (중요)
### ✅ 반드시 지켜야 할 원칙
1) Agent는 외부 API 호출을 직접 하지 않는다 
2) Agent는 Service 구현 세부를 모른다 
3) Agent 간 데이터 전달은 Schema 객체만 사용 
4) Agent 내부에서 dict 남발 ❌

---
# 4. LangGraph 사용 원칙
1) 상태 전이, 분기, 루프가 필요한 Agent만 LangGraph 사용
2) 단순 순차 로직은 일반 함수로 유지
3) LangGraph는 “복잡함을 숨기기 위한 도구”

