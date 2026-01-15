from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

DATABASE_URL = (
    # f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}"
    # f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    f"postgresql://postgres.drlkfjycyvxnpnfqgsxb:UpstageTDA124@aws-1-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()