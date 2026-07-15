import sqlite3

import pytest

from app.services.providers import ProviderUnavailableError, _prepare_question_database
from knowledge.question_bank.repository import QuestionRepository


def _create_sqlite_database(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO marker VALUES ('original')")


def test_serverless_database_is_copied_once(tmp_path):
    source = tmp_path / "source" / "questions.sqlite3"
    runtime_dir = tmp_path / "runtime"
    _create_sqlite_database(source)

    target = _prepare_question_database(source, serverless=True, runtime_dir=runtime_dir)
    original_copy = target.read_bytes()
    source.write_bytes(b"updated source")
    second_target = _prepare_question_database(source, serverless=True, runtime_dir=runtime_dir)

    assert target == runtime_dir / "questions.sqlite3"
    assert second_target == target
    assert target.read_bytes() == original_copy


def test_local_database_uses_original_path(tmp_path):
    source = tmp_path / "questions.sqlite3"
    _create_sqlite_database(source)

    result = _prepare_question_database(
        source,
        serverless=False,
        runtime_dir=tmp_path / "runtime",
    )

    assert result == source
    assert not (tmp_path / "runtime").exists()


def test_missing_source_database_fails_clearly(tmp_path):
    source = tmp_path / "missing" / "questions.sqlite3"

    with pytest.raises(ProviderUnavailableError, match="题库源数据库不存在"):
        _prepare_question_database(
            source,
            serverless=True,
            runtime_dir=tmp_path / "runtime",
        )


def test_repository_does_not_create_missing_database(tmp_path):
    database_path = tmp_path / "nested" / "questions.sqlite3"

    with pytest.raises(FileNotFoundError, match="题库数据库不存在"):
        QuestionRepository(database_path)

    assert database_path.parent.is_dir()
    assert not database_path.exists()
