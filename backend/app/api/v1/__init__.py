"""
API v1 Router - Main API endpoint aggregator

Routes:
- /auth - Authentication endpoints
- /sessions - Session management
- /documents - Document management (PDF upload/download)
- /agents/embedding/* - Embedding agent endpoints
- /agents/general/* - General chat agent endpoints
- /agents/search - Search agent endpoints
- /agents/analysis - Analysis agent endpoints
"""

from fastapi import APIRouter

from app.api.v1 import auth, documents, sessions
from app.api.v1.agents import embedding_router, general_router, search_router, analysis_router

# Create main v1 router
router = APIRouter()

# Include authentication routes
router.include_router(auth.router)

# Include sessions routes
router.include_router(sessions.router)

# Include documents routes
router.include_router(documents.router)

# Include agent routes (unified under /agents)
router.include_router(embedding_router, prefix="/agents")
router.include_router(general_router, prefix="/agents")
router.include_router(search_router, prefix="/agents")
router.include_router(analysis_router, prefix="/agents")
