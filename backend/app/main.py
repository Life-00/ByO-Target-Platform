"""
TVA (Target Validation Assistant) Backend - Main FastAPI Application

AI-powered research platform for academic paper analysis and validation.

Server Configuration:
- Host: 0.0.0.0
- Port: 8000
- Auto-reload: Enabled in debug mode
- CORS: Configured for frontend origins
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1 import router as api_v1_router
from app.config import settings
from app.db import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 TVA (Target Validation Assistant) Backend Starting...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize database
    logger.info("📊 Initializing TVA database...")
    try:
        await DatabaseManager.init()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    logger.info("🔐 JWT Authentication enabled")
    
    yield
    
    # Shutdown
    logger.info("🛑 TVA Backend Shutting Down...")
    try:
        await DatabaseManager.close()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")


# Create FastAPI app
app = FastAPI(
    title="TVA Backend API",
    description="Target Validation Assistant - AI-powered academic research analysis platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add middleware (order matters! CORS must be first)
# CORS (must be added first for preflight requests to work)
logger.info(f"🔐 CORS Origins: {settings.cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZIP compression for response bodies
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ============================================================================
# API Routers
# ============================================================================

app.include_router(
    api_v1_router,
    prefix="/api/v1",
    tags=["v1"],
)


@app.get("/", tags=["system"])
async def root():
    """Root endpoint - API information"""
    return {
        "message": "TVA Backend API",
        "service": "Target Validation Assistant",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint - basic liveness check"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "0.1.0",
    }


@app.get("/ready", tags=["system"])
async def ready_check():
    """Readiness check endpoint - comprehensive dependency check"""
    try:
        # Check database connection
        db_health = await DatabaseManager.health_check()
        if not db_health:
            return {
                "status": "not ready",
                "database": "disconnected",
            }
        
        return {
            "status": "ready",
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Ready check failed: {e}")
        return {
            "status": "not ready",
            "error": str(e),
        }


# Include API routers
app.include_router(
    api_v1_router,
    prefix="/api/v1",
    tags=["v1"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
