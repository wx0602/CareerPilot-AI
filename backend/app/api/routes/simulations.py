from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_token, get_db, owned_training_session
from ...core.errors import api_error, conflict, not_found
from ...core.security import utc_now
from ...dbmodels import AuthToken, Interview, InterviewTurn, Material, Report
from ...schemas.api import (
    ReportResponse,
    SimulationFinishRequest,
    SimulationFinishResponse,
    SimulationGenerateReportRequest,
    SimulationHandleMessageRequest,
    SimulationMessage,
    SimulationStartRequest,
    SimulationTurnResponse,
)
from ...services.providers import ProviderUnavailableError


router = APIRouter(prefix="/simulations", tags=["群体与压力面试"])
SIMULATION_MODES = {"group_interview", "stress_interview"}


def _turns(db: Session, interview_id: str) -> list[InterviewTurn]:
    return list(
        db.scalars(
            select(InterviewTurn)
            .where(InterviewTurn.interview_id == interview_id)
            .order_by(InterviewTurn.ordinal)
        )
    )


def _stored_response(turn: InterviewTurn) -> dict:
    try:
        data = json.loads(turn.question)
    except (TypeError, json.JSONDecodeError) as exc:
        raise api_error(500, "simulation_state_invalid", "模拟面试会话状态损坏") from exc
    if not isinstance(data, dict):
        raise api_error(500, "simulation_state_invalid", "模拟面试会话状态损坏")
    return data


def _api_response(interview: Interview, turn: InterviewTurn) -> SimulationTurnResponse:
    return SimulationTurnResponse(
        interview_id=interview.id,
        turn_id=turn.id,
        **_stored_response(turn),
    )


def _history(turns: list[InterviewTurn]) -> list[dict]:
    history: list[dict] = []
    for turn in turns:
        response = _stored_response(turn)
        history.extend(response.get("messages", []))
        if turn.answer is not None:
            history.append(
                SimulationMessage(
                    message_id=f"user_{turn.id}",
                    speaker="user",
                    display_name="我",
                    content=turn.answer,
                    reply_to=(response.get("messages") or [{}])[-1].get("message_id"),
                ).model_dump()
            )
    return history


def _provider_context(training, materials: list[Material]) -> dict:
    return {
        "candidate_profile": {
            "name": None,
            "target_position": training.position,
            "target_company": training.company,
        },
        "contexts": [chunk for material in materials for chunk in (material.contexts_json or [])],
    }


def _require_simulation_mode(training, mode: str | None = None) -> None:
    if training.mode not in SIMULATION_MODES:
        raise conflict("invalid_simulation_mode", "该训练会话不是群体面试或压力面试")
    if mode is not None and training.mode != mode:
        raise conflict("session_mode_mismatch", "请求模式与训练会话模式不一致")


def _ensure_provider_identity(session_id: str, mode: str, response) -> None:
    if response.session_id != session_id or response.mode != mode:
        raise api_error(502, "invalid_provider_response", "AI 返回的会话或模式不一致")


@router.post("/start-session", response_model=SimulationTurnResponse)
def start_session(
    payload: SimulationStartRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> SimulationTurnResponse:
    training = owned_training_session(payload.session_id, db, token)
    _require_simulation_mode(training, payload.mode)
    interview = db.scalar(select(Interview).where(Interview.session_id == training.id))
    if interview is None:
        interview = Interview(session_id=training.id, mode=training.mode, status="active")
        db.add(interview)
        db.flush()
    turns = _turns(db, interview.id)
    if turns:
        return _api_response(interview, turns[-1])

    materials = list(db.scalars(select(Material).where(Material.session_id == training.id)))
    provider_payload = {
        "session_id": training.id,
        "mode": training.mode,
        "stress_level": payload.stress_level,
        **_provider_context(training, materials),
    }
    try:
        generated = request.app.state.ai_provider.start_session(provider_payload)
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    except ValueError as exc:
        raise api_error(502, "invalid_provider_response", str(exc)) from exc
    validated = SimulationTurnResponse.model_validate(
        {"interview_id": interview.id, "turn_id": str(uuid4()), **generated}
    )
    _ensure_provider_identity(training.id, training.mode, validated)
    turn = InterviewTurn(
        interview_id=interview.id,
        ordinal=1,
        question_id=str(uuid4()),
        question=json.dumps(generated, ensure_ascii=False),
    )
    training.status = "active"
    db.add(turn)
    db.commit()
    db.refresh(turn)
    return validated.model_copy(update={"turn_id": turn.id})


@router.post("/handle-user-message", response_model=SimulationTurnResponse)
def handle_user_message(
    payload: SimulationHandleMessageRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> SimulationTurnResponse:
    training = owned_training_session(payload.session_id, db, token)
    _require_simulation_mode(training)
    interview = db.scalar(select(Interview).where(Interview.session_id == training.id))
    if interview is None:
        raise not_found("模拟面试会话")
    turns = _turns(db, interview.id)
    turn = next((item for item in turns if item.id == payload.turn_id), None)
    if turn is None:
        raise not_found("模拟面试轮次")
    message = payload.message.strip()
    if turn.answer is not None:
        if turn.answer != message:
            raise conflict("turn_already_answered", "该轮已经回答，不能修改发言")
        next_turn = next((item for item in turns if item.ordinal == turn.ordinal + 1), None)
        if next_turn is None:
            raise conflict("simulation_state_invalid", "已回答轮次缺少后续响应")
        return _api_response(interview, next_turn)
    if turns[-1].id != turn.id:
        raise conflict("out_of_order_message", "只能回复当前最新轮次")

    current = _stored_response(turn)
    provider_payload = {
        "session_id": training.id,
        "mode": training.mode,
        "user_message": message,
        "history": _history(turns),
        "stage": current.get("stage"),
        "stress_level": current.get("stress_level"),
    }
    try:
        generated = request.app.state.ai_provider.handle_user_message(provider_payload)
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    except ValueError as exc:
        raise api_error(502, "invalid_provider_response", str(exc)) from exc
    validated = SimulationTurnResponse.model_validate(
        {"interview_id": interview.id, "turn_id": str(uuid4()), **generated}
    )
    _ensure_provider_identity(training.id, training.mode, validated)
    turn.answer = message
    turn.answered_at = utc_now()
    next_turn = InterviewTurn(
        interview_id=interview.id,
        ordinal=turn.ordinal + 1,
        question_id=str(uuid4()),
        question=json.dumps(generated, ensure_ascii=False),
    )
    if generated.get("status") == "completed":
        interview.status = "ready_to_finish"
    db.add(next_turn)
    db.commit()
    db.refresh(next_turn)
    return _api_response(interview, next_turn)


@router.post("/finish-session", response_model=SimulationFinishResponse)
def finish_session(
    payload: SimulationFinishRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> SimulationFinishResponse:
    training = owned_training_session(payload.session_id, db, token)
    _require_simulation_mode(training)
    interview = db.scalar(select(Interview).where(Interview.session_id == training.id))
    if interview is None:
        raise not_found("模拟面试会话")
    turns = _turns(db, interview.id)
    history = _history(turns)
    if not any(item["speaker"] == "user" for item in history):
        raise conflict("no_user_message", "至少完成一轮发言后才能结束并评分")
    saved = next(
        (
            item.evaluation_json["simulation_finish"]
            for item in reversed(turns)
            if item.evaluation_json and "simulation_finish" in item.evaluation_json
        ),
        None,
    )
    if saved is not None:
        return SimulationFinishResponse.model_validate(saved)
    current = _stored_response(turns[-1])
    provider_payload = {
        "session_id": training.id,
        "mode": training.mode,
        "history": history,
        "stage": current.get("stage"),
        "stress_level": current.get("stress_level"),
    }
    try:
        generated = request.app.state.ai_provider.finish_session(provider_payload)
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    except ValueError as exc:
        raise api_error(502, "invalid_provider_response", str(exc)) from exc
    validated = SimulationFinishResponse.model_validate(generated)
    _ensure_provider_identity(training.id, training.mode, validated)
    turns[-1].evaluation_json = {"simulation_finish": validated.model_dump()}
    interview.status = "completed"
    db.commit()
    return validated


@router.post("/generate-report", response_model=ReportResponse)
def generate_report(
    payload: SimulationGenerateReportRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> ReportResponse:
    training = owned_training_session(payload.session_id, db, token)
    _require_simulation_mode(training)
    existing = db.scalar(select(Report).where(Report.session_id == training.id))
    if existing is not None:
        return ReportResponse.model_validate(existing.payload_json)
    interview = db.scalar(select(Interview).where(Interview.session_id == training.id))
    if interview is None:
        raise not_found("模拟面试会话")
    turns = _turns(db, interview.id)
    finish_data = next(
        (
            item.evaluation_json["simulation_finish"]
            for item in reversed(turns)
            if item.evaluation_json and "simulation_finish" in item.evaluation_json
        ),
        None,
    )
    if finish_data is None:
        raise conflict("simulation_not_finished", "请先结束模拟面试并完成评分")
    provider_payload = {
        "session_id": training.id,
        "mode": training.mode,
        "history": _history(turns),
        "evaluation": finish_data["evaluation"],
    }
    try:
        generated = request.app.state.ai_provider.generate_report(provider_payload)
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    except ValueError as exc:
        raise api_error(502, "invalid_provider_response", str(exc)) from exc
    validated = ReportResponse.model_validate(generated)
    _ensure_provider_identity(training.id, training.mode, validated)
    report = Report(session_id=training.id, payload_json=validated.model_dump())
    training.status = "completed"
    training.completed_at = utc_now()
    db.add(report)
    db.commit()
    return validated
