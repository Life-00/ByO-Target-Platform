# Agent 개발 가이드

## 📋 개요

이 디렉토리는 독립적인 AI Agent들을 관리합니다. 각 Agent는 표준화된 구조를 따르며, Agent 팀이 독립적으로 개발하고 백엔드 팀이 최소한의 통합 작업으로 서비스에 추가할 수 있습니다.

---

## 🏗️ 현재 Agent 목록

### 1. GeneralChatAgent
**경로**: `app/agents/general_chat/`  
**용도**: LLM을 사용한 일반 대화, 문서 컨텍스트 기반 질의응답  
**API**: `/api/v1/agents/general/*`

### 2. EmbeddingAgent
**경로**: `app/agents/embedding_agent/`  
**용도**: PDF 문서 처리, 임베딩 생성, 요약 생성  
**API**: `/api/v1/agents/embedding`

---

## 📁 표준 Agent 구조

모든 Agent는 **반드시** 다음 3개 파일을 포함해야 합니다:

```
app/agents/my_agent/
├── __init__.py          # Agent, Request, Response export
├── agent.py             # ✅ REQUIRED - Agent 로직 구현
├── schemas.py           # ✅ REQUIRED - 입출력 스키마 (Pydantic)
└── prompt.py            # ✅ REQUIRED - 프롬프트 템플릿
```

### agent.py
- `BaseAgent` 클래스 상속
- `async execute(request) -> response` 메서드 필수 구현
- Agent 고유 로직 구현
- 외부 서비스 호출 (LLMService, EmbeddingService 등)

### schemas.py
- Pydantic BaseModel 사용
- `{AgentName}Request` - 입력 스키마
- `{AgentName}Response` - 출력 스키마
- 모든 필드에 `Field(..., description="...")` 추가

### prompt.py
- 프롬프트 템플릿 상수
- `SYSTEM_PROMPT` - System message
- 기타 프롬프트 템플릿
- 설정 상수 (DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS 등)

---

## 🚀 신규 Agent 개발 가이드

### Step 1: 기본 구조 생성

```bash
mkdir -p app/agents/my_agent
cd app/agents/my_agent
touch __init__.py agent.py schemas.py prompt.py
```

### Step 2: schemas.py 작성

```python
"""My Agent Schemas"""
from typing import Optional
from pydantic import BaseModel, Field

class MyAgentRequest(BaseModel):
    """입력 스키마"""
    query: str = Field(..., description="사용자 질의")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

class MyAgentResponse(BaseModel):
    """출력 스키마"""
    result: str = Field(..., description="처리 결과")
    tokens_used: int = Field(default=0)
```

### Step 3: prompt.py 작성

```python
"""My Agent Prompts"""

SYSTEM_PROMPT = """You are a specialized AI agent.
Your task is to..."""

DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048
```

### Step 4: agent.py 작성

```python
"""My Agent Implementation"""
import logging
from app.agents.base_agent import BaseAgent
from app.agents.my_agent.schemas import MyAgentRequest, MyAgentResponse
from app.agents.my_agent.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.agent_type = "my_agent"
        self.system_prompt = SYSTEM_PROMPT

    async def execute(self, request: MyAgentRequest) -> MyAgentResponse:
        """Agent 실행 로직"""
        try:
            logger.info(f"[MyAgent] Processing: {request.query}")
            
            # Agent 로직 구현
            result = await self._process(request)
            
            return MyAgentResponse(
                result=result,
                tokens_used=0
            )
        except Exception as e:
            logger.error(f"[MyAgent] Error: {str(e)}")
            raise

    async def _process(self, request: MyAgentRequest) -> str:
        """내부 처리 로직"""
        return f"Processed: {request.query}"
```

### Step 5: __init__.py 작성

```python
"""My Agent Package"""
from .agent import MyAgent
from .schemas import MyAgentRequest, MyAgentResponse

__all__ = ["MyAgent", "MyAgentRequest", "MyAgentResponse"]
```

---

## 🔧 주요 서비스 사용법

### LLMService (채팅 기능)

```python
from app.services.llm_service import get_llm_service

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.llm_service = get_llm_service()

    async def execute(self, request):
        response = await self.llm_service.generate(
            messages=[{"role": "user", "content": request.query}],
            system_prompt=self.system_prompt,
            temperature=0.7,
            max_tokens=2048
        )
        return MyAgentResponse(result=response["content"])
```

### Database (PostgreSQL)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Document

class MyAgent(BaseAgent):
    def __init__(self, db: AsyncSession = None):
        super().__init__()
        self.db = db

    async def execute(self, request):
        if self.db:
            # 조회
            result = await self.db.execute(
                select(Document).where(Document.id == doc_id)
            )
            doc = result.scalar_one_or_none()
            
            # 생성
            new_record = Document(title="New")
            self.db.add(new_record)
            await self.db.commit()
```

### VectorDB (ChromaDB)

```python
from app.services.embedding_service import get_embedding_service
import chromadb

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.embedding_service = get_embedding_service()

    async def execute(self, request):
        # 임베딩 생성
        result = await self.embedding_service.embed(
            text=request.query,
            use_cache=True
        )
        embedding = result["embedding"]
        
        # 유사 문서 검색
        collection = self.chroma_client.get_collection("documents")
        results = collection.query(
            query_embeddings=[embedding],
            n_results=5
        )
```

---

## 🧪 테스트 방법

### 독립 테스트 (권장)

```python
# app/agents/my_agent/test_agent.py
import asyncio
from app.agents.my_agent import MyAgent, MyAgentRequest

async def test():
    agent = MyAgent()
    request = MyAgentRequest(query="Test")
    response = await agent.execute(request)
    print(f"✅ Result: {response.result}")

if __name__ == "__main__":
    asyncio.run(test())
```

**실행:**
```bash
python -m app.agents.my_agent.test_agent
```

### API 엔드포인트 테스트

```bash
curl -X POST http://localhost:8001/api/v1/agents/my-agent \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

---

## 📦 백엔드 통합 (10분 작업)

Agent 팀이 개발 완료 후 백엔드 팀이 수행:

### 1. API 라우터 생성

```python
# app/api/v1/agents/my_agent.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.my_agent import MyAgent, MyAgentRequest, MyAgentResponse
from app.db.database import get_db_session

router = APIRouter(prefix="/my-agent", tags=["agents"])

@router.post("", response_model=MyAgentResponse)
async def execute_agent(
    request: MyAgentRequest,
    db: AsyncSession = Depends(get_db_session)
):
    agent = MyAgent(db=db)
    return await agent.execute(request)
```

### 2. 라우터 등록

```python
# app/api/v1/agents/__init__.py
from .my_agent import router as my_agent_router

routers = [
    general_router,
    embedding_router,
    my_agent_router,  # ✅ 추가
]
```

---

## ✅ 체크리스트

Agent 개발 완료 전 확인:

- [ ] `agent.py`, `schemas.py`, `prompt.py` 3개 파일 존재
- [ ] `BaseAgent` 클래스 상속
- [ ] `execute()` 메서드 구현
- [ ] Request/Response 스키마 정의
- [ ] System prompt 정의
- [ ] 독립 테스트 통과
- [ ] 에러 핸들링 (`try-except`)
- [ ] 로깅 추가 (`logger.info`, `logger.error`)
- [ ] DB 사용 시 commit/rollback 처리
- [ ] Docstring 작성

---

## 📚 참고 자료

- **상세 개발 가이드**: [NEW_AGENT_GUIDE.md](./NEW_AGENT_GUIDE.md)
- **표준 구조 문서**: [AGENT_STRUCTURE.md](./AGENT_STRUCTURE.md)
- **기존 Agent 예제**:
  - GeneralChatAgent: `app/agents/general_chat/`
  - EmbeddingAgent: `app/agents/embedding_agent/`

---

## 💡 핵심 원칙

1. **독립성**: Agent는 독립적으로 개발하고 테스트 가능
2. **표준화**: 모든 Agent는 동일한 구조를 따름
3. **단순성**: 백엔드 통합은 10분 이내에 완료
4. **확장성**: 새로운 Agent 추가가 기존 코드에 영향 없음
