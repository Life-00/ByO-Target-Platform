# 신규 Agent 개발 가이드

## 📋 개요

Agent 팀이 독립적으로 새로운 agent를 개발하고, 백엔드 팀은 최소한의 작업(붙여넣기 + API 라우터 추가)만으로 통합할 수 있도록 설계되었습니다.

---

## 1️⃣ BaseAgent 클래스 상속 및 기본 구조

### 필수 파일 3개

모든 agent는 다음 3개 파일을 **반드시** 포함해야 합니다:

```
app/agents/my_new_agent/
├── __init__.py
├── agent.py          ✅ REQUIRED - Agent 로직
├── schemas.py        ✅ REQUIRED - 입출력 스키마
└── prompt.py         ✅ REQUIRED - 프롬프트 템플릿
```

### 1.1 schemas.py - 입출력 정의

```python
"""
My New Agent Schemas
Input and output data models
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MyAgentRequest(BaseModel):
    """Input schema for my agent"""
    query: str = Field(..., description="User query")
    context: Optional[str] = Field(None, description="Additional context")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=100, le=4096)


class MyAgentResponse(BaseModel):
    """Output schema for my agent"""
    result: str = Field(..., description="Agent response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tokens_used: int = Field(default=0, description="Tokens consumed")
```

### 1.2 prompt.py - 프롬프트 템플릿

```python
"""
My New Agent Prompts
All prompt templates and constants
"""

# System prompt
SYSTEM_PROMPT = """You are a specialized AI agent for [specific task].
Your goal is to [describe the goal].
You should [describe behavior]."""

# User prompt template
USER_PROMPT_TEMPLATE = """Task: {task}

Context: {context}

Please provide a detailed response."""

# Configuration
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048
```

### 1.3 agent.py - Agent 로직

```python
"""
My New Agent Implementation
"""

import logging
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.agents.my_new_agent.schemas import MyAgentRequest, MyAgentResponse
from app.agents.my_new_agent.prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class MyNewAgent(BaseAgent):
    """
    My New Agent
    Specialized for [specific purpose]
    """

    def __init__(self):
        """Initialize agent"""
        super().__init__()
        self.agent_type = "my_new_agent"
        self.system_prompt = SYSTEM_PROMPT

    async def execute(self, request: MyAgentRequest) -> MyAgentResponse:
        """
        Execute agent logic
        
        Args:
            request: MyAgentRequest with input data
            
        Returns:
            MyAgentResponse with results
        """
        try:
            logger.info(f"[MyNewAgent] Processing request: {request.query[:50]}...")

            # Your agent logic here
            result = await self._process(request)

            return MyAgentResponse(
                result=result,
                metadata={"status": "success"},
                tokens_used=0  # Update with actual token count
            )

        except Exception as e:
            logger.error(f"[MyNewAgent] Error: {str(e)}")
            raise

    async def _process(self, request: MyAgentRequest) -> str:
        """Internal processing logic"""
        # Implement your agent logic here
        return f"Processed: {request.query}"
```

### 1.4 __init__.py - Export

```python
"""My New Agent package"""

from .agent import MyNewAgent
from .schemas import MyAgentRequest, MyAgentResponse

__all__ = ["MyNewAgent", "MyAgentRequest", "MyAgentResponse"]
```

---

## 2️⃣ 채팅 서비스(LLM) 사용하기

Agent가 LLM을 호출해야 한다면 **LLMService**를 사용합니다.

### agent.py에 추가

```python
from app.services.llm_service import get_llm_service

class MyNewAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.agent_type = "my_new_agent"
        self.system_prompt = SYSTEM_PROMPT
        self.llm_service = get_llm_service()  # ✅ LLM 서비스 추가

    async def execute(self, request: MyAgentRequest) -> MyAgentResponse:
        try:
            # Build user prompt
            user_prompt = USER_PROMPT_TEMPLATE.format(
                task=request.query,
                context=request.context or "None"
            )

            # Call LLM
            llm_response = await self.llm_service.generate(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=self.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )

            return MyAgentResponse(
                result=llm_response["content"],
                metadata={"model": "solar-1-mini-chat"},
                tokens_used=llm_response["usage"]["total_tokens"]
            )

        except Exception as e:
            logger.error(f"[MyNewAgent] LLM Error: {str(e)}")
            raise
```

**LLMService 메서드:**
- `generate(messages, system_prompt, temperature, max_tokens)` - LLM 호출
- `generate_streaming(...)` - 스트리밍 응답 (필요시)

---

## 3️⃣ PostgreSQL 데이터베이스 접근

Agent가 DB에 접근해야 한다면 **AsyncSession**을 받아서 사용합니다.

### agent.py 수정

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Document, ChatMessage  # 필요한 모델 import

class MyNewAgent(BaseAgent):
    def __init__(self, db: AsyncSession = None):
        super().__init__()
        self.agent_type = "my_new_agent"
        self.system_prompt = SYSTEM_PROMPT
        self.db = db  # ✅ DB 세션 저장

    async def execute(self, request: MyAgentRequest) -> MyAgentResponse:
        try:
            # DB에서 데이터 조회
            if self.db:
                result = await self.db.execute(
                    select(Document).where(Document.id == request.document_id)
                )
                document = result.scalar_one_or_none()
                
                if document:
                    logger.info(f"Found document: {document.title}")

            # DB에 데이터 저장
            if self.db:
                new_record = ChatMessage(
                    session_id=request.session_id,
                    user_id=request.user_id,
                    role="assistant",
                    content="Agent response",
                )
                self.db.add(new_record)
                await self.db.commit()

            return MyAgentResponse(result="Success")

        except Exception as e:
            if self.db:
                await self.db.rollback()
            logger.error(f"[MyNewAgent] DB Error: {str(e)}")
            raise
```

**주요 DB 모델:**
- `Document` - 업로드된 문서
- `ChatMessage` - 채팅 메시지
- `Session` - 세션 정보
- `User` - 사용자 정보

**DB 작업 패턴:**
```python
# 조회
result = await db.execute(select(Model).where(Model.id == id))
item = result.scalar_one_or_none()

# 생성
new_item = Model(field1="value1")
db.add(new_item)
await db.commit()

# 수정
item.field = "new_value"
await db.commit()

# 삭제
await db.delete(item)
await db.commit()
```

---

## 4️⃣ VectorDB(ChromaDB) 사용

문서 임베딩이나 벡터 검색이 필요하다면 **EmbeddingService**를 사용합니다.

### agent.py에 추가

```python
from app.services.embedding_service import get_embedding_service
import chromadb

class MyNewAgent(BaseAgent):
    def __init__(self, db: AsyncSession = None, embedding_service=None):
        super().__init__()
        self.agent_type = "my_new_agent"
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()
        
        # ChromaDB 클라이언트 (필요시)
        from app.config import settings
        self.chroma_client = chromadb.HttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port
        )

    async def execute(self, request: MyAgentRequest) -> MyAgentResponse:
        try:
            # 1. 텍스트를 임베딩으로 변환
            embedding_result = await self.embedding_service.embed(
                text=request.query,
                use_cache=True
            )
            embedding_vector = embedding_result["embedding"]
            
            logger.info(f"Generated embedding: {len(embedding_vector)} dimensions")

            # 2. ChromaDB에서 유사 문서 검색
            collection = self.chroma_client.get_collection(name="documents")
            results = collection.query(
                query_embeddings=[embedding_vector],
                n_results=5,  # Top 5 similar documents
                include=["documents", "metadatas", "distances"]
            )

            similar_docs = results["documents"][0]
            logger.info(f"Found {len(similar_docs)} similar documents")

            # 3. 결과 반환
            return MyAgentResponse(
                result=f"Found {len(similar_docs)} relevant documents",
                metadata={
                    "similar_docs": similar_docs,
                    "distances": results["distances"][0]
                }
            )

        except Exception as e:
            logger.error(f"[MyNewAgent] Vector Error: {str(e)}")
            raise
```

**EmbeddingService 메서드:**
- `embed(text, use_cache)` - 단일 텍스트 임베딩
- `embed_batch(texts, use_cache)` - 배치 임베딩

**ChromaDB 작업:**
```python
# Collection 생성
collection = chroma_client.create_collection(name="my_collection")

# 문서 추가
collection.add(
    documents=["text1", "text2"],
    embeddings=[embedding1, embedding2],
    ids=["id1", "id2"],
    metadatas=[{"key": "value"}, ...]
)

# 검색
results = collection.query(
    query_embeddings=[query_vector],
    n_results=10
)
```

---

## 5️⃣ 테스트 방법

### 5.1 독립적인 Agent 테스트 (추천)

Agent 폴더에 테스트 파일 생성:

```python
# app/agents/my_new_agent/test_agent.py

import asyncio
from app.agents.my_new_agent import MyNewAgent, MyAgentRequest

async def test_agent():
    """Test agent independently"""
    
    # Agent 초기화
    agent = MyNewAgent()
    
    # 테스트 요청 생성
    request = MyAgentRequest(
        query="Test query",
        context="Test context",
        temperature=0.7,
        max_tokens=1024
    )
    
    # 실행
    response = await agent.execute(request)
    
    # 결과 확인
    print(f"✅ Result: {response.result}")
    print(f"✅ Tokens: {response.tokens_used}")
    print(f"✅ Metadata: {response.metadata}")

if __name__ == "__main__":
    asyncio.run(test_agent())
```

**실행:**
```bash
cd /home/mei22/tva/backend
python -m app.agents.my_new_agent.test_agent
```

### 5.2 API 엔드포인트 테스트

백엔드 팀이 API 라우터를 추가한 후:

```python
# app/api/v1/agents/my_new_agent.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.my_new_agent import MyNewAgent, MyAgentRequest, MyAgentResponse
from app.db.database import get_db_session

router = APIRouter(prefix="/my-new-agent", tags=["agents"])

@router.post("", response_model=MyAgentResponse)
async def execute_agent(
    request: MyAgentRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Execute MyNewAgent"""
    agent = MyNewAgent(db=db)
    return await agent.execute(request)
```

**curl 테스트:**
```bash
curl -X POST http://localhost:8001/api/v1/agents/my-new-agent \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Test query",
    "context": "Test context"
  }'
```

### 5.3 통합 테스트 (pytest)

```python
# tests/agents/test_my_new_agent.py

import pytest
from app.agents.my_new_agent import MyNewAgent, MyAgentRequest

@pytest.mark.asyncio
async def test_agent_execute():
    """Test agent execution"""
    agent = MyNewAgent()
    request = MyAgentRequest(query="Test", context="Context")
    
    response = await agent.execute(request)
    
    assert response.result is not None
    assert response.tokens_used >= 0

@pytest.mark.asyncio
async def test_agent_with_db(db_session):
    """Test agent with database"""
    agent = MyNewAgent(db=db_session)
    request = MyAgentRequest(query="Test", context="Context")
    
    response = await agent.execute(request)
    
    assert response.result is not None
```

**실행:**
```bash
pytest tests/agents/test_my_new_agent.py -v
```

---

## 📦 백엔드 팀 통합 작업 (최소화)

Agent 팀이 완성한 agent를 통합하려면:

### 1. Agent 폴더 복사
```bash
cp -r my_new_agent/ app/agents/
```

### 2. API 라우터 생성 (5분 작업)
```python
# app/api/v1/agents/my_new_agent.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.my_new_agent import MyNewAgent, MyAgentRequest, MyAgentResponse
from app.db.database import get_db_session
from app.services.embedding_service import get_embedding_service

router = APIRouter(prefix="/my-new-agent", tags=["agents"])

@router.post("", response_model=MyAgentResponse)
async def execute_agent(
    request: MyAgentRequest,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        agent = MyNewAgent(
            db=db,
            embedding_service=get_embedding_service()  # 필요시
        )
        return await agent.execute(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 3. 라우터 등록
```python
# app/api/v1/agents/__init__.py

from .my_new_agent import router as my_new_agent_router

# app/api/v1/__init__.py에서:
router.include_router(my_new_agent_router, prefix="/agents")
```

---

## ✅ 체크리스트

Agent 개발 완료 전 확인사항:

- [ ] `agent.py`, `schemas.py`, `prompt.py` 3개 파일 존재
- [ ] `BaseAgent` 클래스 상속
- [ ] `execute()` 메서드 구현
- [ ] Input/Output 스키마 정의 (Pydantic)
- [ ] System prompt 정의
- [ ] 독립 테스트 통과 (`test_agent.py`)
- [ ] 에러 핸들링 구현
- [ ] 로깅 추가 (`logger.info`, `logger.error`)
- [ ] DB 사용 시 rollback 처리
- [ ] 문서화 (docstring 작성)

---

## 🚀 예제: 실제 Agent 참고

프로젝트에 이미 구현된 agent들을 참고하세요:

1. **GeneralChatAgent** (`app/agents/general_chat/`)
   - LLMService 사용 예제
   - 문서 컨텍스트 처리
   
2. **EmbeddingAgent** (`app/agents/embedding_agent/`)
   - DB + VectorDB 사용 예제
   - PDF 처리 및 임베딩

---

## 📝 요약

| 작업 | Agent 팀 | 백엔드 팀 |
|------|---------|----------|
| Agent 로직 개발 | ✅ 100% | - |
| 독립 테스트 | ✅ 100% | - |
| 폴더 복사 | - | ✅ 1분 |
| API 라우터 추가 | - | ✅ 5분 |
| 통합 테스트 | - | ✅ 5분 |

**총 소요시간:** Agent 팀 (2-3일), 백엔드 팀 (10분) ⚡
