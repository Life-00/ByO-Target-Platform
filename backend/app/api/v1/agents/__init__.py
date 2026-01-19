"""
Agent API Routes

Unified agent endpoints:
- /agents/embedding/* - EmbeddingAgent routes
- /agents/general/* - GeneralChatAgent routes
- /agents/search - SearchAgent routes
- /agents/analysis - AnalysisAgent routes
- /agents/report/* - ReportAgent routes
"""

from .embedding import router as embedding_router
from .general import router as general_router
from .search import router as search_router
from .analysis import router as analysis_router
from .report import router as report_router

__all__ = ["embedding_router", "general_router", "search_router", "analysis_router", "report_router"]
