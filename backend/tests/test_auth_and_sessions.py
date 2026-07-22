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


def test_user_profile_can_be_updated_and_includes_stats(client: TestClient):
    registered = client.post(
        "/api/auth/register",
        json={"account": "profile@test.local", "password": "Secret123!"},
    ).json()
    headers = auth_headers(registered["access_token"])

    initial = client.get("/api/auth/me", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["user"]["nickname"] is None
    assert initial.json()["stats"]["answered_questions"] == 0

    updated = client.patch(
        "/api/auth/me",
        headers=headers,
        json={
            "nickname": "小林同学",
            "avatar_preset": "violet",
            "target_position": "Java 后端工程师",
            "career_stage": "new_grad",
        },
    )
    assert updated.status_code == 200
    updated_user = updated.json()["user"]
    assert updated_user["nickname"] == "小林同学"
    assert updated_user["avatar_preset"] == "violet"
    assert updated_user["target_position"] == "Java 后端工程师"
    assert updated_user["career_stage"] == "new_grad"

    question = {
        "question_id": "profile-favorite",
        "question_type": "true_false",
        "content": "这是一道收藏统计测试题。",
        "options": [],
    }
    assert client.post("/api/favorites", headers=headers, json={"question": question}).status_code == 201
    refreshed = client.get("/api/auth/me", headers=headers).json()
    assert refreshed["user"]["nickname"] == "小林同学"
    assert refreshed["stats"]["favorite_questions"] == 1


def test_guest_profile_is_read_only(client: TestClient):
    guest = client.post("/api/auth/guest").json()
    headers = auth_headers(guest["access_token"])
    profile = client.get("/api/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["user"]["is_guest"] is True

    rejected = client.patch(
        "/api/auth/me",
        headers=headers,
        json={"nickname": "游客昵称", "avatar_preset": "blue"},
    )
    assert rejected.status_code == 403


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


def test_confirming_a_module_starts_a_fresh_exam_and_refresh_keeps_it(logged_in):
    client, headers = logged_in
    question_mix = {
        "single_choice": 1,
        "multiple_choice": 0,
        "true_false": 0,
        "short_answer": 0,
    }
    session = client.post(
        "/api/training-sessions",
        headers=headers,
        json={
            "mode": "technical",
            "learning_module": "java_backend",
            "learning_module_title": "Java 后端",
            "question_mix": question_mix,
        },
    ).json()

    first = client.post(
        "/api/exams/generate",
        headers=headers,
        json={
            "session_id": session["session_id"],
            "position": session["position"],
            "learning_module": session["learning_module"],
            "learning_module_title": session["learning_module_title"],
            "question_mix": question_mix,
        },
    ).json()

    updated = client.patch(
        f"/api/training-sessions/{session['session_id']}",
        headers=headers,
        json={
            "position": "Python 后端工程师",
            "learning_module": "python_backend",
            "learning_module_title": "Python 后端",
            "question_mix": question_mix,
        },
    ).json()
    second_response = client.post(
        "/api/exams/generate",
        headers=headers,
        json={
            "session_id": updated["session_id"],
            "position": updated["position"],
            "learning_module": updated["learning_module"],
            "learning_module_title": updated["learning_module_title"],
            "question_mix": question_mix,
        },
    )
    assert second_response.status_code == 200
    second = second_response.json()
    assert second["exam_id"] != first["exam_id"]
    assert second["session_id"] == first["session_id"]
    assert "Python" in second["title"]
    assert all("Python" in item["content"] for item in second["questions"])

    refreshed = client.post(
        "/api/exams/generate",
        headers=headers,
        json={
            "session_id": updated["session_id"],
            "position": updated["position"],
            "learning_module": updated["learning_module"],
            "learning_module_title": updated["learning_module_title"],
            "question_mix": question_mix,
        },
    ).json()
    assert refreshed["exam_id"] == second["exam_id"]


def test_switching_company_position_starts_a_fresh_exam(logged_in):
    client, headers = logged_in
    question_mix = {
        "single_choice": 1,
        "multiple_choice": 0,
        "true_false": 0,
        "short_answer": 0,
    }
    session = client.post(
        "/api/training-sessions",
        headers=headers,
        json={
            "mode": "technical",
            "company": "alibaba",
            "position": "engineering",
            "learning_module": "company_exam",
            "learning_module_title": "研发岗",
            "question_mix": question_mix,
        },
    ).json()
    first = client.post(
        "/api/exams/generate",
        headers=headers,
        json={
            "session_id": session["session_id"],
            "company": session["company"],
            "position": session["position"],
            "learning_module": session["learning_module"],
            "learning_module_title": session["learning_module_title"],
            "question_mix": question_mix,
        },
    ).json()

    updated = client.patch(
        f"/api/training-sessions/{session['session_id']}",
        headers=headers,
        json={
            "position": "algorithm",
            "learning_module_title": "算法岗",
            "question_mix": question_mix,
        },
    ).json()
    second = client.post(
        "/api/exams/generate",
        headers=headers,
        json={
            "session_id": updated["session_id"],
            "company": updated["company"],
            "position": updated["position"],
            "learning_module": updated["learning_module"],
            "learning_module_title": updated["learning_module_title"],
            "question_mix": question_mix,
        },
    ).json()

    assert second["exam_id"] != first["exam_id"]
