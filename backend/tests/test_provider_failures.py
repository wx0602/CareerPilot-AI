from starlette.testclient import TestClient

from app.db.base import Base
from app.main import create_app
from tests.conftest import auth_headers


DEFAULT_MIX = {
    "single_choice": 5,
    "true_false": 5,
    "multiple_choice": 2,
    "short_answer": 3,
}


def test_real_mode_connects_c_and_d_providers(settings):
    real_settings = settings.model_copy(update={"provider_mode": "real"})
    application = create_app(settings=real_settings)
    Base.metadata.create_all(application.state.engine)
    with TestClient(application) as client:
        login = client.post(
            "/api/auth/login",
            json={"account": "demo@test.local", "password": "Demo123!"},
        )
        headers = auth_headers(login.json()["access_token"])
        session_id = client.post(
            "/api/training-sessions",
            headers=headers,
            json={"mode": "technical"},
        ).json()["session_id"]

        upload = client.post(
            "/api/materials/upload",
            headers=headers,
            data={"session_id": session_id, "material_type": "resume"},
            files={"file": ("resume.txt", "后端开发，熟悉 Redis 和 Java。", "text/plain")},
        )
        assert upload.status_code == 201
        assert upload.json()["parse_status"] == "parsed"

        exam = client.post(
            "/api/exams/generate",
            headers=headers,
            json={"session_id": session_id, "position": "Java 后端工程师", "question_count": 1},
        )
        assert exam.status_code == 200
        serialized = str(exam.json()).lower()
        assert "correct_answer" not in serialized
        assert "explanation" not in serialized


def test_real_mode_generates_unique_questions_with_difficulty_fallback(settings):
    real_settings = settings.model_copy(update={"provider_mode": "real"})
    application = create_app(settings=real_settings)
    Base.metadata.create_all(application.state.engine)
    with TestClient(application) as client:
        login = client.post(
            "/api/auth/login",
            json={"account": "demo@test.local", "password": "Demo123!"},
        )
        headers = auth_headers(login.json()["access_token"])
        session_id = client.post(
            "/api/training-sessions",
            headers=headers,
            json={
                "mode": "technical",
                "position": "Java 后端工程师",
                "learning_module": "java_backend",
                "learning_module_title": "Java 后端",
                "question_mix": DEFAULT_MIX,
            },
        ).json()["session_id"]

        response = client.post(
            "/api/exams/generate",
            headers=headers,
            json={
                "session_id": session_id,
                "position": "Java 后端工程师",
                "difficulty": "medium",
                "learning_module": "java_backend",
                "learning_module_title": "Java 后端",
                "question_mix": DEFAULT_MIX,
            },
        )

        assert response.status_code == 200
        questions = response.json()["questions"]
        assert len(questions) == sum(DEFAULT_MIX.values())
        assert len({item["question_id"] for item in questions}) == len(questions)
        assert len({item["content"] for item in questions}) == len(questions)
        assert [item["question_type"] for item in questions] == (
            ["single_choice"] * 5
            + ["multiple_choice"] * 2
            + ["true_false"] * 5
            + ["short_answer"] * 3
        )
        assert {
            question_type: sum(item["question_type"] == question_type for item in questions)
            for question_type in DEFAULT_MIX
        } == DEFAULT_MIX
