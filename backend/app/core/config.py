from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        enable_decoding=False,
    )

    PROJECT_NAME: str = "AI-Powered Cold Email CRM"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "development"

    # Runtime
    FRONTEND_PORT: int = 3000
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8050
    BACKEND_URL: str = "http://127.0.0.1:8050"
    NEXT_PUBLIC_API_URL: str = "/api/v1"

    # Security
    SECRET_KEY: str = "dev-only-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database / Redis
    POSTGRES_URL: str = "postgresql://user:password@127.0.0.1:5432/cold_email_crm"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # External APIs
    OPENAI_API_KEY: str | None = None

    # Mailcow API Integration
    MAILCOW_API_URL: str | None = None
    MAILCOW_API_KEY: str | None = None
    MAILCOW_API_TIMEOUT_SECONDS: int = 10
    MAILCOW_VERIFY_SSL: bool = True
    MAILCOW_SMTP_HOST: str | None = None
    MAILCOW_SMTP_PORT: int = 587
    MAILCOW_IMAP_HOST: str | None = None
    MAILCOW_IMAP_PORT: int = 993

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if not value:
            return ["http://localhost:3000"]
        return [item.strip() for item in str(value).split(",") if item.strip()]

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"development", "test", "staging", "production"}
        if normalized not in allowed:
            raise ValueError(f"APP_ENV must be one of: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("NEXT_PUBLIC_API_URL")
    @classmethod
    def validate_public_api_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("NEXT_PUBLIC_API_URL must be a relative path such as /api/v1")
        return cleaned.rstrip("/") or "/api/v1"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters long")
        return cleaned

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "Settings":
        if not self.POSTGRES_URL:
            raise ValueError("POSTGRES_URL is required")
        if not self.REDIS_URL:
            raise ValueError("REDIS_URL is required")
        if self.APP_ENV != "test" and self.SECRET_KEY in {
            "dev-only-change-me",
            "super-secret-key-for-development-only-change-in-production",
            "change-me-to-a-strong-random-string",
        }:
            raise ValueError(
                "SECRET_KEY is using an unsafe placeholder. Set a local value in .env before starting the app."
            )
        has_mailcow_url = bool(self.MAILCOW_API_URL)
        has_mailcow_key = bool(self.MAILCOW_API_KEY)
        if has_mailcow_url != has_mailcow_key:
            raise ValueError("MAILCOW_API_URL and MAILCOW_API_KEY must be set together")
        return self


settings = Settings()
