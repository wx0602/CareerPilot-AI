def _create_session(client, headers, mode):
    response = client.post(
        "/api/training-sessions",
        headers=headers,
        json={"mode": mode, "position": "产品经理"},
    )
    assert response.status_code == 201
    return response.json()["session_id"]


def test_group_interview_full_flow_uses_existing_session_storage(logged_in):
    client, headers = logged_in
    session_id = _create_session(client, headers, "group_interview")

    started = client.post(
        "/api/simulations/start-session",
        headers=headers,
        json={"session_id": session_id, "mode": "group_interview"},
    )
    assert started.status_code == 200
    assert started.json()["stage"] == "case_intro"

    handled = client.post(
        "/api/simulations/handle-user-message",
        headers=headers,
        json={
            "session_id": session_id,
            "turn_id": started.json()["turn_id"],
            "message": "我建议先按收益、风险和资源占用建立权重，再形成项目排序。",
        },
    )
    assert handled.status_code == 200
    candidate_messages = [
        item for item in handled.json()["messages"] if item["speaker"].startswith("candidate_")
    ]
    candidate_ids = {item["message_id"] for item in candidate_messages}
    assert len(candidate_messages) == 3
    assert any(item.get("reply_to") in candidate_ids for item in candidate_messages)

    finished = client.post(
        "/api/simulations/finish-session",
        headers=headers,
        json={"session_id": session_id},
    )
    assert finished.status_code == 200
    assert set(finished.json()["evaluation"]["dimension_scores"]) == {
        "逻辑",
        "表达",
        "参与度",
        "协作",
        "倾听",
        "领导力",
        "冲突处理",
        "总结能力",
    }
    assert all(
        evidence["quote"] == "我建议先按收益、风险和资源占用建立权重，再形成项目排序。"
        for evidence in finished.json()["evaluation"]["evidence"]
    )

    report = client.post(
        "/api/simulations/generate-report",
        headers=headers,
        json={"session_id": session_id},
    )
    assert report.status_code == 200
    assert report.json()["mode"] == "group_interview"
    assert report.json()["charts"]["evidence"]
    assert client.get("/api/reports", headers=headers).json()[0]["session_id"] == session_id


def test_stress_interview_immediately_honors_pressure_controls(logged_in):
    client, headers = logged_in
    session_id = _create_session(client, headers, "stress_interview")
    started = client.post(
        "/api/simulations/start-session",
        headers=headers,
        json={"session_id": session_id, "mode": "stress_interview", "stress_level": "high"},
    )
    assert started.status_code == 200
    assert started.json()["stress_level"] == "high"

    lowered = client.post(
        "/api/simulations/handle-user-message",
        headers=headers,
        json={
            "session_id": session_id,
            "turn_id": started.json()["turn_id"],
            "message": "请降低压力",
        },
    )
    assert lowered.status_code == 200
    assert lowered.json()["control_acknowledged"] is True
    assert lowered.json()["stress_level"] == "medium"

    paused = client.post(
        "/api/simulations/handle-user-message",
        headers=headers,
        json={
            "session_id": session_id,
            "turn_id": lowered.json()["turn_id"],
            "message": "暂停",
        },
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    assert paused.json()["control_acknowledged"] is True


def test_simulation_openapi_exposes_unified_contract(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/api/simulations/start-session",
        "/api/simulations/handle-user-message",
        "/api/simulations/finish-session",
        "/api/simulations/generate-report",
    } <= set(paths)
