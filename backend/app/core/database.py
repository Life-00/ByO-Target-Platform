import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings


def build_database_url() -> str:
    base = (
        f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASSWORD}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )

    sslmode = (settings.DB_SSLMODE or "").strip()

    if sslmode:
        return f"{base}?sslmode={sslmode}"
    return base


DATABASE_URL = build_database_url()

print(f"[{time.strftime('%H:%M:%S')}] [DB-INIT] Preparing connection for {settings.DB_HOST}...")
print(f"[{time.strftime('%H:%M:%S')}] [DB-INIT] Using sslmode={settings.DB_SSLMODE}")

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    connect_args={
        "connect_timeout": 30
    },
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
