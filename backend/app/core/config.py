import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    UPSTAGE_API_KEY: str
    UPSTAGE_BASE_URL: str
    UPSTAGE_MODEL: str
    UPSTAGE_EMBED_MODEL: str
    
    JWT_SECRET_KEY: str = "your-very-secret-key-here" 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "target_validation_papers"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

print(f"--- ENVIRONMENT SETTINGS LOADED ---")
print(f"MODEL: {settings.UPSTAGE_MODEL}")