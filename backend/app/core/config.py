import os
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


def _is_serverless_runtime(task_root: Path = Path("/var/task")) -> bool:
    runtime_markers = (
        "VERCEL",
        "VERCEL_ENV",
        "AWS_LAMBDA_FUNCTION_NAME",
        "LAMBDA_TASK_ROOT",
    )
    return any(os.environ.get(name) for name in runtime_markers) or task_root.is_dir()


IS_SERVERLESS = _is_serverless_runtime()
RUNTIME_DIR = Path("/tmp/careerpilot") if IS_SERVERLESS else BACKEND_DIR


def _resolve_backend_relative_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (BACKEND_DIR / path).resolve()


def _normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)

    prefix = "sqlite:///"
    if not value.startswith(prefix):
        return value
    raw_path = value.removeprefix(prefix)
    if raw_path in {":memory:", ""}:
        return value
    return f"{prefix}{_resolve_backend_relative_path(raw_path).as_posix()}"


class Settings(BaseSettings):
    app_name: str = "CareerPilot AI API"
    app_env: str = "production" if IS_SERVERLESS else "development"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'careerpilot.db').as_posix()}"
    upload_dir: Path = RUNTIME_DIR / "uploads"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_origin_regex: str | None = None
    max_upload_bytes: int = 10 * 1024 * 1024
    provider_mode: str = "real"
    knowledge_database_path: str = str(
        REPO_ROOT / "knowledge" / "question_bank" / "questions.sqlite3"
    )
    knowledge_chroma_dir: str = str(
        RUNTIME_DIR / "chroma_store"
        if IS_SERVERLESS
        else REPO_ROOT / "knowledge" / "chroma_store"
    )
    knowledge_raw_dir: str = str(REPO_ROOT / "knowledge" / "question_bank" / "raw")
    ai_core_path: str = str(REPO_ROOT / "ai-core")

    demo_account: str = "demo@careerpilot.local"
    demo_password: str = "Demo123!"
    auth_token_ttl_hours: int = 24
    remember_token_ttl_days: int = 30
    guest_token_ttl_hours: int = 2
    jsearch_api_key: str | None = None
    jsearch_base_url: str = "https://api.openwebninja.com/jsearch/search-v2"
    jsearch_timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return _normalize_database_url(value)

    @field_validator(
        "upload_dir",
        "knowledge_database_path",
        "knowledge_chroma_dir",
        "knowledge_raw_dir",
        "ai_core_path",
        mode="after",
    )
    @classmethod
    def normalize_paths(cls, value: str | Path) -> Path | str:
        resolved = _resolve_backend_relative_path(value)
        return resolved if isinstance(value, Path) else str(resolved)

    @model_validator(mode="after")
    def validate_production_database(self) -> "Settings":
        if self.app_env == "production" and self.database_url.startswith("sqlite"):
            raise ValueError("生产环境不能使用 SQLite，请配置 DATABASE_URL 为 Postgres 连接串")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings()
