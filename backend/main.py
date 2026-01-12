import uvicorn
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine
from app.models.user_db import Base  
from app.api.v1 import auth, chat

app = FastAPI(title="Target Validation Assistant")

print(f"[{time.strftime('%H:%M:%S')}] [ORM] Checking and creating tables in Supabase...")
Base.metadata.create_all(bind=engine) 
print(f"[{time.strftime('%H:%M:%S')}] [ORM] Table synchronization complete.")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://54.82.11.131","http://54.82.11.131:80",],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

@app.get("/")
def root():
    return {"message": "Server is running with SQLAlchemy ORM"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
