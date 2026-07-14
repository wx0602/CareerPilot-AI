from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import BACKEND_DIR, Settings, _is_serverless_runtime


def test_lambda_runtime_is_detected_without_vercel_marker(monkeypatch, tmp_path):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("LAMBDA_TASK_ROOT", "/var/task")

    assert _is_serverless_runtime(task_root=tmp_path / "missing") is True


def test_local_runtime_is_not_detected_as_serverless(monkeypatch, tmp_path):
    for name in ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT"):
        monkeypatch.delenv(name, raising=False)

    assert _is_serverless_runtime(task_root=tmp_path / "missing") is False


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
