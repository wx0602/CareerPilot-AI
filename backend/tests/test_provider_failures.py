from starlette.testclient import TestClient

from app.db.base import Base
from app.main import create_app
from tests.conftest import auth_headers


def test_real_mode_reports_missing_c_and_d_providers(settings):
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
            files={"file": ("resume.txt", "后端开发", "text/plain")},
        )
        assert upload.status_code == 201
        assert upload.json()["parse_status"] == "failed"

        exam = client.post(
            "/api/exams/generate",
            headers=headers,
            json={"session_id": session_id, "position": "后端工程师", "question_count": 1},
        )
        assert exam.status_code == 503
        assert exam.json()["detail"]["code"] == "ai_provider_unavailable"
