# ScholarLens Backend

AI-powered academic research analysis platform backend.

## 📋 Overview

ScholarLens Backend is a FastAPI-based system that powers the research analysis platform. It features:

- **4 Modular AI Agents**: Search, PDF Analysis, RAG Q&A, Report Generation
- **PostgreSQL Database**: Comprehensive data management with 9 normalized tables
- **ChromaDB Vector DB**: Semantic search with single collection architecture
- **Upstage API Integration**: LLM and embedding services
- **Central LLM Config**: Unified prompt, persona, and few-shot management
- **Docker Ready**: Complete containerization with PostgreSQL, ChromaDB, Redis

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (for containerized setup)
- UV package manager (or pip)
- Upstage API Key

### Local Development Setup

```bash
# Clone and enter backend directory
cd backend

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# Especially: UPSTAGE_API_KEY

# Install dependencies with UV
uv pip install -e .

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Docker Setup

```bash
# Build and run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Run migrations in container
docker-compose exec backend alembic upgrade head

# Access
# API: http://localhost:8001
# Docs: http://localhost:8001/docs
```

## 📁 Project Structure

```
backend/
├── .env                          # Environment variables (git ignored)
├── .env.example                  # Example configuration
├── docker-compose.yml            # Docker services
├── Dockerfile                    # Backend container
├── pyproject.toml               # UV dependencies
│
├── app/
│   ├── config/                  # ✨ Central configuration
│   │   ├── settings.py          # Environment & LLM settings
│   │   ├── llm_prompts.py       # Prompt templates
│   │   └── few_shot_examples.py # Few-shot examples (in llm_prompts.py)
│   │
│   ├── main.py                  # FastAPI application
│   │
│   ├── db/                      # Database layer
│   │   ├── models.py            # SQLAlchemy ORM
│   │   ├── database.py          # Connection management
│   │   └── migrations/          # Alembic migrations
│   │
│   ├── services/                # Business logic
│   │   ├── user_service.py
│   │   ├── session_service.py
│   │   ├── document_service.py
│   │   └── report_service.py
│   │
│   ├── agents/                  # AI Agents (completely modular)
│   │   ├── base_agent.py
│   │   │
│   │   ├── search_indexer/      # Agent 1: Paper Search
│   │   ├── pdf_analyzer/        # Agent 2: PDF Analysis
│   │   ├── rag_agent/           # Agent 3: Q&A
│   │   ├── report_writer/       # Agent 4: Report Generation
│   │   │
│   │   └── common/              # Shared utilities
│   │       ├── llm_client.py    # ✨ Central LLM client
│   │       ├── prompt_builder.py
│   │       └── embedding.py
│   │
│   └── api/v1/                  # API routes
│       └── __init__.py
│
├── tests/                        # Test suite
└── uploads/                      # User file uploads
```

## 🤖 Central LLM Configuration

### How It Works

All Agent prompts, personas, and few-shot examples are centrally managed in `app/config/`:

```python
# app/config/llm_prompts.py
SYSTEM_PROMPTS = {
    "rag_agent": "You are an expert...",
    "report_writer": "You are an expert report writer...",
    # ...
}

PERSONAS = {
    "rag_agent": {...},
    "report_writer": {...},
    # ...
}

PROMPT_TEMPLATES = {
    "answer_question": "Based on {context}, answer {question}...",
    "generate_report": "Write a report on {topic}...",
    # ...
}
```

### Agent Usage Example

```python
from app.config import LLMClient

# Agent uses central config automatically
client = LLMClient("rag_agent")
response = await client.call_llm(
    prompt_template="answer_question",
    template_vars={
        "question": "What is CRISPR?",
        "context": "..."
    }
)
# Internally:
# 1. Retrieves system prompt for rag_agent
# 2. Injects persona description
# 3. Adds few-shot examples
# 4. Calls Upstage LLM with complete prompt
```

### Updating Prompts/Personas

To update all agents' behavior, modify a single file:

```python
# 1. Edit app/config/llm_prompts.py
# 2. All agents automatically use new settings on next request
# 3. No need to modify individual agent files
```

## 🔗 Database Architecture

### PostgreSQL Schema (9 Tables)

- **users**: Authentication & profiles
- **sessions**: Research sessions
- **documents**: PDF uploads & metadata
- **document_annotations**: Analysis results
- **chat_messages**: Q&A history
- **analysis_reports**: Generated reports
- **agent_logs**: Agent execution tracking
- **api_usage**: API call metrics
- **migrations**: Schema version tracking

### ChromaDB (Single Collection)

- **documents_chunks**: All document embeddings
  - Metadata filtering: session_id, document_id, source_section
  - Enables: RAG search, section-based filtering

## 🚀 Running the Backend

### Development

```bash
# Terminal 1: Start services
docker-compose up -d postgres chromadb redis

# Terminal 2: Run FastAPI
uvicorn app.main:app --reload

# Access: http://localhost:8000/docs
```

### Production

```bash
# Build and run full stack
docker-compose -f docker-compose.yml up -d

# Check health
curl http://localhost:8001/health

# View logs
docker-compose logs -f backend
```

## 🛠️ API Endpoints (Phase 1)

- `GET /health` - Health check
- `GET /ready` - Ready check with dependency status
- `GET /docs` - Swagger UI documentation
- `GET /api/v1/status` - API status

## 📦 Dependencies

### Core
- **fastapi==0.109.0**: Web framework
- **sqlalchemy==2.0.23**: ORM
- **psycopg==3.1.14**: PostgreSQL driver
- **chromadb==0.4.18**: Vector database
- **upstage**: LLM & embedding API

### Processing
- **pypdf==4.0.1**: PDF reading
- **pdfplumber==0.10.3**: PDF extraction
- **python-docx==0.8.11**: Word document support

### Tools
- **httpx==0.25.2**: Async HTTP client
- **redis==5.0.1**: Caching
- **alembic==1.13.1**: Database migrations

See `pyproject.toml` for complete dependency list.

## 🔑 Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# APIs
UPSTAGE_API_KEY=your_api_key

# LLM Configuration
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000

# Server
ENVIRONMENT=development
DEBUG=true
```

See `.env.example` for all available options.

## 📚 Development

### Code Style
- Black for formatting
- Ruff for linting
- MyPy for type checking

```bash
# Format code
black app tests

# Lint
ruff check app tests

# Type check
mypy app
```

### Testing
```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v

# Rebuild containers
docker-compose build --no-cache
```

## 📈 Next Steps

### Phase 1 (Current)
- [x] Project initialization
- [x] Docker setup
- [x] Central LLM configuration
- [ ] Database models & migrations
- [ ] Basic API routes
- [ ] Agent base classes

### Phase 2
- [ ] Agent 1: Search Indexer
- [ ] Agent 2: PDF Analyzer
- [ ] Agent 3: RAG Agent
- [ ] Agent 4: Report Writer

### Phase 3
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Monitoring & logging
- [ ] Production deployment

## 📝 License

MIT License - See LICENSE file

## 👥 Contributors

ScholarLens Team

---

**Created**: 2026-01-17  
**Status**: Phase 1 - Initialization  
**Python**: 3.12+  
**Package Manager**: UV
