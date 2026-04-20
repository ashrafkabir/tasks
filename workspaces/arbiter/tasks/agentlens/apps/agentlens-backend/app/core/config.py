from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgentLens API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "change_me_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    # Using SQLite for development velocity (Pivot from PostgreSQL)
    SQLALCHEMY_DATABASE_URL: str = "sqlite:///./agentlens.db"
    
    # PostgreSQL Fields (to satisfy Pydantic validation from .env)
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    postgres_host: Optional[str] = None
    postgres_port: Optional[str] = None
    
    # LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # CORS
    # Added allowedDevOrigins to solve the Next.js communication issue
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"  # This is the real fix

settings = Settings()
