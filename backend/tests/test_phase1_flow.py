from starlette.testclient import TestClient


def test_complete_technical_flow_and_idempotency(logged_in):
    client, headers = logged_in
    session = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": "technical", "position": "后端开发工程师", "company": "示例企业"},
    )
    assert session.status_code == 201
    session_id = session.json()["session_id"]

    paper_response = client.post(
        "/api/exams/generate",
        headers=headers,
        json={
            "session_id": session_id,
            "position": "后端开发工程师",
            "company": "示例企业",
            "difficulty": "medium",
            "question_count": 3,
        },
    )
    assert paper_response.status_code == 200
    paper = paper_response.json()
    serialized = str(paper).lower()
    assert "correct_answer" not in serialized
    assert "explanation" not in serialized
    assert all("answer" not in question for question in paper["questions"])

    answers = [
        {"question_id": "stub-1", "answer": "B"},
        {"question_id": "stub-2", "answer": "true"},
        {"question_id": "stub-3", "answer": "索引可以提高查询速度但会增加写入维护成本。"},
    ]
    submission_payload = {
        "session_id": session_id,
        "exam_id": paper["exam_id"],
        "answers": answers,
    }
    result = client.post("/api/exams/submit", headers=headers, json=submission_payload)
    assert result.status_code == 200
    assert result.json()["score"] == 90

    repeated = client.post(
        "/api/exams/submit",
        headers=headers,
        json={**submission_payload, "answers": list(reversed(answers))},
    )
    assert repeated.status_code == 200
    changed = client.post(
        "/api/exams/submit",
        headers=headers,
        json={
            **submission_payload,
            "answers": [{"question_id": "stub-1", "answer": "A"}],
        },
    )
    assert changed.status_code == 409
    saved_result = client.get(f"/api/exams/{paper['exam_id']}/result", headers=headers)
    assert saved_result.json() == result.json()

    first_question = client.post(
        "/api/interviews/message", headers=headers, json={"session_id": session_id}
    )
    assert first_question.status_code == 200
    question = first_question.json()["next_question"]
    answer_payload = {
        "session_id": session_id,
        "question_id": question["question_id"],
        "answer": "我负责接口开发。",
    }
    evaluated = client.post("/api/interviews/message", headers=headers, json=answer_payload)
    assert evaluated.status_code == 200
    assert evaluated.json()["is_followup"] is True
    assert evaluated.json()["evaluation"]["need_followup"] is True
    repeated_answer = client.post(
        "/api/interviews/message", headers=headers, json=answer_payload
    )
    assert repeated_answer.json() == evaluated.json()

    report = client.post(
        "/api/reports/generate", headers=headers, json={"session_id": session_id}
    )
    assert report.status_code == 200
    assert report.json()["mode"] == "technical"
    assert report.json()["overall_score"] > 0
    assert client.get(f"/api/reports/{session_id}", headers=headers).json() == report.json()


def test_report_requires_a_result(logged_in):
    client, headers = logged_in
    session_id = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": "technical"},
    ).json()["session_id"]
    response = client.post(
        "/api/reports/generate", headers=headers, json={"session_id": session_id}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "no_training_result"


def test_report_can_be_generated_from_exam_only(logged_in):
    client, headers = logged_in
    session_id = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": "technical"},
    ).json()["session_id"]
    paper = client.post(
        "/api/exams/generate",
        headers=headers,
        json={"session_id": session_id, "position": "后端工程师", "question_count": 1},
    ).json()
    client.post(
        "/api/exams/submit",
        headers=headers,
        json={
            "session_id": session_id,
            "exam_id": paper["exam_id"],
            "answers": [{"question_id": "stub-1", "answer": "B"}],
        },
    )
    report = client.post(
        "/api/reports/generate", headers=headers, json={"session_id": session_id}
    )
    assert report.status_code == 200
    assert report.json()["overall_score"] == 100
    assert report.json()["nonverbal_score"] is None
    saved_reports = client.get("/api/reports", headers=headers)
    assert saved_reports.status_code == 200
    assert saved_reports.json()[0]["session_id"] == session_id
    assert saved_reports.json()[0]["overall_score"] == 100


def test_report_can_be_generated_from_interview_only(logged_in):
    client, headers = logged_in
    session_id = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": "technical"},
    ).json()["session_id"]
    question = client.post(
        "/api/interviews/message", headers=headers, json={"session_id": session_id}
    ).json()["next_question"]
    client.post(
        "/api/interviews/message",
        headers=headers,
        json={
            "session_id": session_id,
            "question_id": question["question_id"],
            "answer": "我会先复现问题，再结合日志、指标和调用链逐层定位根因。",
        },
    )
    report = client.post(
        "/api/reports/generate", headers=headers, json={"session_id": session_id}
    )
    assert report.status_code == 200
    assert report.json()["overall_score"] > 0


def _create_completed_job_interview(client, headers):
    session_id = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": "job", "position": "后端工程师"},
    ).json()["session_id"]
    question = client.post(
        "/api/interviews/message", headers=headers, json={"session_id": session_id}
    ).json()["next_question"]
    response = client.post(
        "/api/interviews/message",
        headers=headers,
        json={
            "session_id": session_id,
            "question_id": question["question_id"],
            "answer": "我会先明确岗位目标，再用项目成果和数据说明自己的匹配度。",
        },
    )
    assert response.status_code == 200
    return session_id


def _valid_nonverbal_score(total_score=86):
    return {
        "status": "complete",
        "reason": None,
        "message": None,
        "total_score": total_score,
        "dimensions": {
            "camera_attention": 90,
            "body_posture": 84,
            "movement_stability": 85,
            "interaction_state": 88,
            "facial_dynamics": 80,
        },
        "statistics": {
            "question_count": 1,
            "sample_count": 40,
            "valid_face_samples": 25,
            "analyzed_duration_seconds": 10.2,
            "face_presence_ratio": 0.96,
            "no_face_events": 0,
            "head_deviation_events": 0,
            "posture_events": 0,
            "movement_events": 0,
            "average_response_delay_seconds": 2.4,
        },
        "strengths": ["大部分回答时间保持在摄像头画面内。"],
        "suggestions": ["继续保持自然交流。"],
    }


def _insufficient_nonverbal_score():
    return {
        "status": "insufficient_data",
        "reason": "answer_too_short",
        "message": "有效回答视频时间过短，本次未生成可靠的非语言表现评分。",
        "total_score": None,
        "dimensions": None,
        "statistics": {
            "question_count": 0,
            "sample_count": 0,
            "valid_face_samples": 0,
            "analyzed_duration_seconds": 0,
            "face_presence_ratio": 0,
            "no_face_events": 0,
            "head_deviation_events": 0,
            "posture_events": 0,
            "movement_events": 0,
            "average_response_delay_seconds": None,
        },
        "strengths": [],
        "suggestions": [],
    }


def test_nonverbal_score_is_saved_read_and_not_overwritten(logged_in):
    client, headers = logged_in
    session_id = _create_completed_job_interview(client, headers)
    original = _valid_nonverbal_score()
    generated = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"session_id": session_id, "nonverbal_score": original},
    )
    assert generated.status_code == 200
    assert generated.json()["nonverbal_score"] == original
    assert client.get(f"/api/reports/{session_id}", headers=headers).json()["nonverbal_score"] == original
    listed = client.get("/api/reports", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["nonverbal_score"] == original

    repeated = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"session_id": session_id, "nonverbal_score": _valid_nonverbal_score(20)},
    )
    assert repeated.status_code == 200
    assert repeated.json()["nonverbal_score"] == original


def test_insufficient_nonverbal_score_can_be_upgraded_once(logged_in):
    client, headers = logged_in
    session_id = _create_completed_job_interview(client, headers)
    initial = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"session_id": session_id, "nonverbal_score": _insufficient_nonverbal_score()},
    )
    assert initial.status_code == 200
    assert initial.json()["nonverbal_score"]["status"] == "insufficient_data"

    upgraded_score = _valid_nonverbal_score(73)
    upgraded = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"session_id": session_id, "nonverbal_score": upgraded_score},
    )
    assert upgraded.status_code == 200
    assert upgraded.json()["nonverbal_score"] == upgraded_score
    assert client.get(f"/api/reports/{session_id}", headers=headers).json()["nonverbal_score"] == upgraded_score

    repeated = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"session_id": session_id, "nonverbal_score": _valid_nonverbal_score(10)},
    )
    assert repeated.status_code == 200
    assert repeated.json()["nonverbal_score"] == upgraded_score


def test_nonverbal_score_rejects_invalid_status_and_out_of_range_score(logged_in):
    client, headers = logged_in
    invalid_status = client.post(
        "/api/reports/generate",
        headers=headers,
        json={
            "session_id": "validation-only",
            "nonverbal_score": {**_valid_nonverbal_score(), "status": "unknown"},
        },
    )
    assert invalid_status.status_code == 422

    out_of_range = _valid_nonverbal_score()
    out_of_range["dimensions"]["camera_attention"] = 101
    invalid_score = client.post(
        "/api/reports/generate",
        headers=headers,
        json={"session_id": "validation-only", "nonverbal_score": out_of_range},
    )
    assert invalid_score.status_code == 422


def test_openapi_contains_all_phase_one_routes(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        "/api/auth/login",
        "/api/auth/guest",
        "/api/auth/logout",
        "/api/training-sessions",
        "/api/materials/upload",
        "/api/exams/generate",
        "/api/exams/submit",
        "/api/exams/{exam_id}/result",
        "/api/interviews/message",
        "/api/reports/generate",
        "/api/reports/{session_id}",
        "/health",
    }
    assert expected <= set(paths)
