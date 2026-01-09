# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, chat

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], # 프론트엔드 주소 명시
    allow_credentials=True,
    allow_methods=["*"], # 모든 메서드 허용 (GET, POST, OPTIONS 등)
    allow_headers=["*"], # 모든 헤더 허용 (Content-Type, Authorization 등)
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

@app.get("/")
def read_root():
    return {"message": "Target Validation API is running"}

