import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Cold Email CRM"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-for-development-only-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    # Comma-separated list of allowed origins
    ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    
    # Database
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "postgresql://user:password@localhost:5432/cold_email_crm")
    
    # Redis & Celery
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # External APIs
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

    # Mailcow API Integration
    MAILCOW_API_URL: str | None = os.getenv("MAILCOW_API_URL")
    MAILCOW_API_KEY: str | None = os.getenv("MAILCOW_API_KEY")

settings = Settings()
