from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CareerPilot AI API"
    app_env: str = "development"
    database_url: str = "sqlite:///./careerpilot.db"
    upload_dir: Path = Path("./uploads")
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_bytes: int = 10 * 1024 * 1024
    provider_mode: str = "stub"
    knowledge_database_path: str = "knowledge/question_bank/questions.sqlite3"
    knowledge_chroma_dir: str = "knowledge/chroma_store"
    knowledge_raw_dir: str = "knowledge/question_bank/raw"
    ai_core_path: str = "ai-core"

    demo_account: str = "demo@careerpilot.local"
    demo_password: str = "Demo123!"
    auth_token_ttl_hours: int = 24
    remember_token_ttl_days: int = 30
    guest_token_ttl_hours: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def get_settings() -> Settings:
    return Settings()
