import pytest

from agents.supervisor_agent import SupervisorAgent
from agents.group_interview_agent import GroupInterviewAgent
from agents.stress_interview_agent import StressInterviewAgent
from models import (
    EvidenceReference,
    SimulationEvaluation,
    SimulationMessage,
    SimulationTurnResponse,
    SimulationUserMessageRequest,
)
from scoring.simulation import (
    GROUP_DIMENSIONS,
    detect_stress_control,
    lower_stress_level,
    validate_evaluation,
)


def _evaluation(quote: str) -> SimulationEvaluation:
    return SimulationEvaluation(
        overall_score=80,
        dimension_scores={dimension: 80 for dimension in GROUP_DIMENSIONS},
        evidence=[
            EvidenceReference(dimension=dimension, quote=quote, rationale="引用用户原话")
            for dimension in GROUP_DIMENSIONS
        ],
    )


def test_supervisor_routes_new_modes_to_dedicated_agents():
    supervisor = SupervisorAgent()
    assert supervisor(
        {"task_type": "start_session", "request": {"mode": "group_interview"}}
    )["next_agent"] == "group_interview_agent"
    assert supervisor(
        {"task_type": "handle_user_message", "request": {"mode": "stress_interview"}}
    )["next_agent"] == "stress_interview_agent"
    assert supervisor(
        {"task_type": "generate_report", "request": {"mode": "technical"}}
    )["next_agent"] == "report_agent"


def test_scoring_evidence_must_quote_real_user_message():
    history = [
        SimulationMessage(
            message_id="user-1",
            speaker="user",
            display_name="我",
            content="我建议先统一评价标准，再按风险和收益排序。",
        )
    ]
    validate_evaluation("group_interview", _evaluation("统一评价标准"), history)
    with pytest.raises(ValueError, match="不是用户真实发言"):
        validate_evaluation("group_interview", _evaluation("用户从未说过的话"), history)


def test_stress_controls_are_deterministic():
    assert detect_stress_control("请立即停止") == "stop"
    assert detect_stress_control("暂停一下") == "pause"
    assert detect_stress_control("请降低压力") == "lower"
    assert lower_stress_level("high") == "medium"
    assert lower_stress_level("medium") == "light"
    assert lower_stress_level("light") == "light"


def test_stress_agent_handles_stop_without_calling_llm(monkeypatch):
    agent = StressInterviewAgent()
    monkeypatch.setattr(
        agent,
        "_call",
        lambda *args, **kwargs: pytest.fail("控制口令不应调用大模型"),
    )
    response = agent.handle_user_message(
        SimulationUserMessageRequest(
            session_id="session-1",
            mode="stress_interview",
            user_message="停止",
            stress_level="high",
        )
    )
    assert response.status == "completed"
    assert response.control_acknowledged is True


def test_group_agent_requires_all_candidates_and_cross_response():
    request = SimulationUserMessageRequest(
        session_id="session-1",
        mode="group_interview",
        user_message="先统一标准。",
    )
    response = SimulationTurnResponse(
        session_id="session-1",
        mode="group_interview",
        stage="free_discussion",
        messages=[
            SimulationMessage(message_id="a", speaker="candidate_logic", display_name="陈析", content="建立标准。"),
            SimulationMessage(message_id="b", speaker="candidate_collaboration", display_name="周和", content="同意。", reply_to="a"),
            SimulationMessage(message_id="c", speaker="candidate_challenger", display_name="秦问", content="需要验证。", reply_to="a"),
        ],
    )
    GroupInterviewAgent._validate_candidate_exchange(request, response)
    response.messages.pop()
    with pytest.raises(ValueError, match="三种 AI 候选人"):
        GroupInterviewAgent._validate_candidate_exchange(request, response)


def test_group_stage_progression_is_deterministic():
    assert GroupInterviewAgent._next_stage("case_intro") == "individual_statement"
    assert GroupInterviewAgent._next_stage("individual_statement") == "free_discussion"
    assert GroupInterviewAgent._next_stage("free_discussion") == "disagreement_resolution"
    assert GroupInterviewAgent._next_stage("disagreement_resolution") == "consensus"
    assert GroupInterviewAgent._next_stage("consensus") == "summary"
    assert GroupInterviewAgent._next_stage("summary") == "scoring"
    assert GroupInterviewAgent._next_stage("scoring") == "scoring"
