from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        upload_dir=tmp_path / "uploads",
        max_upload_bytes=1024,
        provider_mode="stub",
        demo_account="demo@test.local",
        demo_password="Demo123!",
    )


@pytest.fixture
def app(settings: Settings):
    application = create_app(settings=settings)
    Base.metadata.create_all(application.state.engine)
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def logged_in(client: TestClient) -> tuple[TestClient, dict[str, str]]:
    response = client.post(
        "/api/auth/login",
        json={"account": "demo@test.local", "password": "Demo123!"},
    )
    assert response.status_code == 200
    return client, auth_headers(response.json()["access_token"])
