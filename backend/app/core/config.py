"""Application configuration and settings."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "postgresql://ai_consultant:ai_consultant_password@db:5432/ai_consultant_db"

    # API
    api_title: str = "Consulting Engine API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LLM
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_model: str = "gpt-4-turbo-preview"

    # File upload
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_extensions: list[str] = [".csv"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


