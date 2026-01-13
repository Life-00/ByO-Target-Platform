import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# 라우터들 (분리한 구조 기준)
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.files import router as files_router
from app.api.v1.research import router as research_router
from app.api.v1.selections import router as selections_router
from app.api.v1.extract import router as extract_router
from app.api.v1.report import router as report_router

from app.core.database import engine
from app.models.base import Base

app = FastAPI(title="Target Validation Assistant")

print(f"[{time.strftime('%H:%M:%S')}] [APP] Starting...")

@app.on_event("startup")
def on_startup():
    if settings.AUTO_CREATE_TABLES:
        print("[DB] Auto-create enabled")
        Base.metadata.create_all(bind=engine)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
print(f"[{time.strftime('%H:%M:%S')}] [CORS] Allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# Router mount
app.include_router(auth_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(research_router, prefix="/api/v1")
app.include_router(selections_router, prefix="/api/v1")
app.include_router(extract_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")

# chat도 /api/v1로 붙이되, 라우터 내부에서 /sessions/{id}/chat 경로를 사용
app.include_router(chat_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "ok"}
