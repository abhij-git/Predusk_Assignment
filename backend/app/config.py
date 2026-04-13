from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (parent of app/) — stable regardless of process cwd
_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        env_file=(
            str(_BACKEND_ROOT / ".env"),
            str(_BACKEND_ROOT / ".env.local"),
        ),
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/docflow"
    sync_database_url: str = "postgresql://postgres:postgres@localhost:5432/docflow"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    upload_dir: str = str(_BACKEND_ROOT / "uploads")
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"


settings = Settings()
