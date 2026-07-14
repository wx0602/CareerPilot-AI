from starlette.testclient import TestClient

from tests.conftest import auth_headers


def test_login_logout_and_invalid_password(client: TestClient):
    invalid = client.post(
        "/api/auth/login",
        json={"account": "demo@test.local", "password": "wrong"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["detail"]["code"] == "unauthorized"

    login = client.post(
        "/api/auth/login",
        json={"account": "DEMO@test.local", "password": "Demo123!", "remember_me": True},
    )
    assert login.status_code == 200
    headers = auth_headers(login.json()["access_token"])
    created = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": "technical", "position": "后端工程师"},
    )
    assert created.status_code == 201

    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    rejected = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": "technical"},
    )
    assert rejected.status_code == 401


def test_guest_can_create_only_one_training_session(client: TestClient):
    guest = client.post("/api/auth/guest").json()
    headers = auth_headers(guest["access_token"])
    first = client.post(
        "/api/training-sessions", headers=headers, json={"mode": "technical"}
    )
    assert first.status_code == 201
    second = client.post(
        "/api/training-sessions", headers=headers, json={"mode": "technical"}
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "guest_session_limit"


def test_training_session_ownership_is_enforced(client: TestClient):
    first_token = client.post("/api/auth/guest").json()["access_token"]
    second_token = client.post("/api/auth/guest").json()["access_token"]
    first_headers = auth_headers(first_token)
    second_headers = auth_headers(second_token)
    session_id = client.post(
        "/api/training-sessions",
        headers=first_headers,
        json={"mode": "technical"},
    ).json()["session_id"]
    denied = client.post(
        "/api/exams/generate",
        headers=second_headers,
        json={"session_id": session_id, "position": "后端工程师", "question_count": 1},
    )
    assert denied.status_code == 403
