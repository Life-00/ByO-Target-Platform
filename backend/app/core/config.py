import time
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Upstage
    UPSTAGE_API_KEY: str
    UPSTAGE_BASE_URL: str
    UPSTAGE_MODEL: str
    UPSTAGE_EMBED_MODEL: str

    # JWT
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # DB
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Postgres sslmode 값: disable / prefer / require / verify-ca / verify-full
    DB_SSLMODE: str = "disable"

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

print(f"[{time.strftime('%H:%M:%S')}] [CONFIG] Environment settings loaded.")
print(f"  - Target Model: {settings.UPSTAGE_MODEL}")
