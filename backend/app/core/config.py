import time
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# 로컬 개발 시 .env 로드 (운영에서는 환경변수/CI로 주입)
load_dotenv()


# /app/app/core/config.py -> parents[2] = /app
APP_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # ---------- Upstage ----------
    UPSTAGE_API_KEY: str
    UPSTAGE_BASE_URL: str = "https://api.upstage.ai/v1"
    UPSTAGE_MODEL: str = "solar-pro2"
    UPSTAGE_EMBED_MODEL: str = "solar-embedding-1-large"

    # ---------- JWT/Auth ----------
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ---------- Postgres ----------
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "tva-db"
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_SSLMODE: str = "disable"

    # ---------- Chroma ----------
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # ---------- CORS ------------
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:80,http://localhost"

    AUTO_CREATE_TABLES: bool = True

    # ---------- NCBI (PMC/PubMed) ----------
    NCBI_EMAIL: str
    NCBI_TOOL: str

    # ---------- Storage ----------
    # 프로젝트 루트 기준 업로드/다운로드 저장 폴더 (기본: /app/uploads)
    UPLOAD_DIR: str = "uploads"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def get_uploads_dir() -> Path:
    """
    항상 '절대경로'로 통일된 uploads 디렉토리를 돌려줍니다.
    (상대경로 저장으로 인해 DB에 pdf_storage_path가 null 되는 문제 방지)
    """
    d = (APP_ROOT / settings.UPLOAD_DIR).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


# 너무 시끄러우면 지워도 됨(민감값은 찍지 않음)
print(f"[{time.strftime('%H:%M:%S')}] [CONFIG] Loaded. UPSTAGE_MODEL={settings.UPSTAGE_MODEL} APP_ROOT={APP_ROOT} UPLOAD_DIR={get_uploads_dir()}")
