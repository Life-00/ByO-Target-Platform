"""
Global application settings
All configuration from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Literal
import logging
from zoneinfo import ZoneInfo

class Settings(BaseSettings):
    """Global application settings"""
    
    # Timezone (Korea Standard Time)
    timezone: ZoneInfo = ZoneInfo("Asia/Seoul")
    
    # Database
    database_url: str
    
    # ChromaDB
    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    chroma_db_path: str = "./chroma_data"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    enable_caching: bool = True
    cache_ttl: int = 3600  # seconds
    
    # API Keys
    upstage_api_key: str
    
    # JWT Configuration (from .env)
    jwt_secret_key: str = "tva-backend-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    refresh_token_expire_days: int = 7
    
    # Backward compatibility
    @property
    def secret_key(self) -> str:
        """Backward compatibility for secret_key"""
        return self.jwt_secret_key
    
    @property
    def algorithm(self) -> str:
        """Backward compatibility for algorithm"""
        return self.jwt_algorithm
    
    # LLM Configuration
    upstage_llm_model: str = "solar-1-mini-chat"
    upstage_embedding_model: str = "embedding-passage"  # Upstage embedding model
    llm_model: str = "upstage-solar-pro"  # Legacy
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000
    llm_top_p: float = 0.9
    
    # Agent Configuration
    agent_timeout: int = 60
    agent_retry_count: int = 3
    
    # Server
    environment: Literal["development", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000,http://localhost:8001"
    
    @property
    def cors_origins(self) -> list:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    # Upload
    max_upload_size: int = 52428800  # 50MB
    upload_directory: str = "./uploads"
    
    @property
    def upload_directory_abs(self) -> str:
        """Get absolute path to upload directory"""
        from pathlib import Path
        return str(Path(self.upload_directory).resolve())
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

# Global settings instance
settings = Settings()

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
