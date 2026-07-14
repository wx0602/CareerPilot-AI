from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import BACKEND_DIR, Settings


def test_relative_runtime_paths_are_resolved_from_backend_directory():
    settings = Settings(
        database_url="sqlite:///./runtime.db",
        upload_dir=Path("./runtime-uploads"),
    )

    assert settings.database_url == f"sqlite:///{(BACKEND_DIR / 'runtime.db').as_posix()}"
    assert settings.upload_dir == BACKEND_DIR / "runtime-uploads"


@pytest.mark.parametrize("scheme", ["postgres://", "postgresql://"])
def test_postgres_url_uses_psycopg_driver(scheme: str):
    settings = Settings(
        app_env="production",
        database_url=f"{scheme}user:password@example.com/careerpilot?sslmode=require",
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.database_url.endswith("?sslmode=require")


def test_production_rejects_sqlite_database():
    with pytest.raises(ValidationError, match="Postgres"):
        Settings(app_env="production", database_url="sqlite:///./production.db")
