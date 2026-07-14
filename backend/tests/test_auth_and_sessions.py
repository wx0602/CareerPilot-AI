from starlette.testclient import TestClient

from tests.conftest import auth_headers


def test_register_login_and_duplicate_account(client: TestClient):
    registered = client.post(
        "/api/auth/register",
        json={"account": "new-user@test.local", "password": "Secret123!"},
    )
    assert registered.status_code == 201
    assert registered.json()["user"]["account"] == "new-user@test.local"

    duplicate = client.post(
        "/api/auth/register",
        json={"account": "NEW-USER@test.local", "password": "Secret123!"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "account_exists"

    login = client.post(
        "/api/auth/login",
        json={"account": "new-user@test.local", "password": "Secret123!"},
    )
    assert login.status_code == 200


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


def test_favorite_questions_are_persisted(client: TestClient):
    guest = client.post("/api/auth/guest").json()
    headers = auth_headers(guest["access_token"])
    question = {
        "question_id": "fav-q1",
        "question_type": "single_choice",
        "content": "下面哪个选项是缓存组件？",
        "options": [{"key": "A", "text": "Redis"}, {"key": "B", "text": "HTML"}],
    }
    created = client.post("/api/favorites", headers=headers, json={"question": question})
    assert created.status_code == 201
    assert created.json()["question_id"] == "fav-q1"

    repeated = client.post("/api/favorites", headers=headers, json={"question": question})
    assert repeated.status_code == 201
    assert repeated.json()["favorite_id"] == created.json()["favorite_id"]

    listed = client.get("/api/favorites", headers=headers)
    assert listed.status_code == 200
    assert [item["question_id"] for item in listed.json()] == ["fav-q1"]

    removed = client.delete("/api/favorites/fav-q1", headers=headers)
    assert removed.status_code == 204
    assert client.get("/api/favorites", headers=headers).json() == []


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
