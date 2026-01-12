import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

DATABASE_URL = (
    f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@"
    f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?sslmode=require"
)

print(f"[{time.strftime('%H:%M:%S')}] [DB-INIT] Preparing connection for {settings.DB_HOST}...")

engine = create_engine(
    DATABASE_URL, 
    poolclass=NullPool,
    connect_args={
        "connect_timeout": 30  
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    print(f"[{time.strftime('%H:%M:%S')}] [DB-SESSION] New DB session opened.")
    try:
        yield db
    finally:
        db.close()
        print(f"[{time.strftime('%H:%M:%S')}] [DB-SESSION] DB session closed.")