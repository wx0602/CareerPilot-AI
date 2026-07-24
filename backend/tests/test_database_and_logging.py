import json
from time import sleep
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import OperationalError
from starlette.testclient import TestClient

from app.api.deps import get_db
from app.core.config import BACKEND_DIR
from app.db.base import Base
from app.db.session import create_database_engine, create_session_factory
from app.dbmodels import User
from app.main import create_app


def test_alembic_upgrade_reaches_database_index_revision(tmp_path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(BACKEND_DIR / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_database_engine(database_url, slow_query_ms=0)
    try:
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        assert revision == "20260724_0005"
        report_indexes = {item["name"] for item in inspect(engine).get_indexes("reports")}
        assert "ix_reports_generated_at" in report_indexes
    finally:
        engine.dispose()


def test_sqlite_engine_enables_reliability_pragmas_and_indexes(tmp_path):
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'reliable.db').as_posix()}",
        sqlite_busy_timeout_ms=4321,
        slow_query_ms=0,
    )
    try:
        Base.metadata.create_all(engine)
        with engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
            assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 4321
            assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"

        indexes = {item["name"] for item in inspect(engine).get_indexes("training_sessions")}
        assert "ix_training_sessions_owner_created" in indexes
        assert "ix_training_sessions_token_created" in indexes
    finally:
        engine.dispose()


def test_database_dependency_rolls_back_failed_request(app):
    request = SimpleNamespace(app=app)
    dependency = get_db(request)
    db = next(dependency)
    db.add(User(account="rollback@test.local", password_hash="not-a-real-hash"))
    db.flush()

    with pytest.raises(RuntimeError, match="force rollback"):
        dependency.throw(RuntimeError("force rollback"))

    with app.state.session_factory() as verification:
        count = verification.scalar(
            select(func.count(User.id)).where(User.account == "rollback@test.local")
        )
    assert count == 0


def test_request_log_contains_trace_fields_without_sensitive_body(settings, tmp_path):
    log_dir = tmp_path / "logs"
    application = create_app(
        settings=settings.model_copy(
            update={
                "log_to_file": True,
                "log_dir": log_dir,
                "slow_query_ms": 1,
            }
        )
    )
    Base.metadata.create_all(application.state.engine)
    with application.state.engine.connect() as connection:
        connection.connection.driver_connection.create_function(
            "sleep_ms",
            1,
            lambda milliseconds: sleep(milliseconds / 1000),
        )
        connection.execute(text("SELECT sleep_ms(5)"))

    with TestClient(application) as client:
        response = client.post(
            "/api/auth/login",
            headers={"X-Request-ID": "test.request-123"},
            json={"account": "demo@test.local", "password": "NeverWriteThisPassword"},
        )
        health = client.get("/health", headers={"X-Request-ID": "invalid request id"})

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "test.request-123"
    assert health.status_code == 200
    assert len(health.headers["X-Request-ID"]) == 32
    assert health.json()["database"]["foreign_keys"] is True

    serialized = (log_dir / "app.log").read_text(encoding="utf-8")
    records = [json.loads(line) for line in serialized.splitlines()]
    request_record = next(
        item
        for item in records
        if item.get("event") == "http_request"
        and item.get("request_id") == "test.request-123"
    )
    assert request_record["method"] == "POST"
    assert request_record["path"] == "/api/auth/login"
    assert request_record["status_code"] == 401
    assert request_record["duration_ms"] >= 0
    assert any(item.get("event") == "slow_database_query" for item in records)
    assert "NeverWriteThisPassword" not in serialized
    assert "Authorization" not in serialized


def test_database_error_returns_safe_503_response_without_sql_parameters(settings, tmp_path):
    log_dir = tmp_path / "database-error-logs"
    application = create_app(
        settings=settings.model_copy(update={"log_to_file": True, "log_dir": log_dir})
    )
    Base.metadata.create_all(application.state.engine)

    @application.get("/_test/database-error")
    def database_error_route():
        raise OperationalError(
            "SELECT secret FROM private_table WHERE password=:password",
            {"password": "SensitiveSqlParameter"},
            RuntimeError("database offline"),
        )

    with TestClient(application) as client:
        response = client.get(
            "/_test/database-error",
            headers={"X-Request-ID": "database-test"},
        )

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "database-test"
    assert response.json() == {
        "detail": {
            "code": "database_unavailable",
            "message": "数据库暂时不可用，请稍后重试",
        }
    }
    serialized = (log_dir / "app.log").read_text(encoding="utf-8")
    assert "SensitiveSqlParameter" not in serialized
    assert "private_table" not in serialized
