import pytest
from types import SimpleNamespace
from app.agents.search_agent.agent import SearchAgent
from app.agents.search_agent.schemas import SearchAgentRequest

pytestmark = pytest.mark.asyncio

class DummyLLM:
    def __init__(self, count=3, score=0.9):
        self.count = count
        self.score = score
    async def generate(self, messages, system_prompt=None, temperature=None, max_tokens=None):
        text = messages[0]["content"]
        if "requested_count" in text:
            return {"content": '{"requested_count": %d}' % self.count}
        if "Paper Information" in text:
            return {"content": '{"relevance_score": %.2f}' % self.score}
        return {"content": "gene editing crispr delivery"}

class DummySession:
    async def execute(self, *a, **kw): return SimpleNamespace(scalars=lambda: [])
    async def flush(self): pass
    async def commit(self): pass
    async def rollback(self): pass

@pytest.fixture
def patch_mocks(monkeypatch):
    async def fake_search_biorxiv(query, max_results):
        return [{
            "title": "CRISPR delivery",
            "abstract": "Short abstract",
            "doi": "10.1101/12345",
            "preprint_id": "12345",
            "source": "biorxiv",
            "authors": ["A", "B", "C", "D"],
            "published_date": "2025-01-01",
            "pdf_url": "https://www.biorxiv.org/content/10.1101/12345.full.pdf",
        }]
    monkeypatch.setattr("app.agents.search_agent.agent.search_biorxiv", fake_search_biorxiv)

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: DummyLLM())

    async def fake_download_pdfs(papers, session_id, user_id, uploads_dir, db):
        return {"paths": ["/tmp/fake.pdf"], "document_ids": [42]}
    monkeypatch.setattr("app.agents.search_agent.agent.download_pdfs", fake_download_pdfs)

async def test_search_agent_basic(patch_mocks):
    agent = SearchAgent(db=DummySession())
    req = SearchAgentRequest(
        session_id=1, user_id=1,
        content="find latest gene editing delivery methods",
        analysis_goal="compare delivery",
        max_results=1,
        min_relevance_score=0.5,
        selected_documents=[]
    )
    resp = await agent.execute(req)
    assert resp.success is True
    assert resp.papers_downloaded == 1
    assert resp.papers[0].doi == "10.1101/12345"
    assert resp.papers[0].source == "biorxiv"