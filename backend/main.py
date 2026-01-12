import uvicorn
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine
from app.models.user_db import Base
from app.api.v1 import auth, chat
from app.core.config import settings

app = FastAPI(title="Target Validation Assistant")

print(f"[{time.strftime('%H:%M:%S')}] [ORM] Checking and creating tables...")
Base.metadata.create_all(bind=engine)
print(f"[{time.strftime('%H:%M:%S')}] [ORM] Table synchronization complete.")

# CORS
origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

print(f"[{time.strftime('%H:%M:%S')}] [CORS] Allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# Router
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

@app.get("/")
def root():
    return {"message": "Server is running with SQLAlchemy ORM"}
