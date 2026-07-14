from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_token, get_db, owned_training_session
from app.core.errors import api_error, conflict, not_found
from app.core.security import utc_now
from app.dbmodels import (
    AuthToken,
    Exam,
    ExamSubmission,
    Interview,
    InterviewTurn,
    Report,
)
from app.schemas.api import ReportGenerateRequest, ReportResponse
from app.services.providers import ProviderUnavailableError


router = APIRouter(prefix="/reports", tags=["报告"])


@router.post("/generate", response_model=ReportResponse)
def generate_report(
    payload: ReportGenerateRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> ReportResponse:
    training = owned_training_session(payload.session_id, db, token)
    existing = db.scalar(select(Report).where(Report.session_id == training.id))
    if existing is not None:
        return ReportResponse.model_validate(existing.payload_json)

    exam = db.scalar(select(Exam).where(Exam.session_id == training.id))
    submission = (
        db.scalar(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id))
        if exam is not None
        else None
    )
    interview = db.scalar(select(Interview).where(Interview.session_id == training.id))
    turns = (
        list(
            db.scalars(
                select(InterviewTurn)
                .where(
                    InterviewTurn.interview_id == interview.id,
                    InterviewTurn.evaluation_json.is_not(None),
                )
                .order_by(InterviewTurn.ordinal)
            )
        )
        if interview is not None
        else []
    )
    if submission is None and not turns:
        raise conflict("no_training_result", "至少完成笔试或一轮面试后才能生成报告")
    provider_request = {
        "session_id": training.id,
        "mode": training.mode,
        "exam_result": submission.result_json if submission else None,
        "interview_evaluations": [turn.evaluation_json for turn in turns],
    }
    try:
        generated = request.app.state.ai_provider.generate_report(provider_request)
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    validated = ReportResponse.model_validate(generated)
    if validated.session_id != training.id or validated.mode != training.mode:
        raise api_error(502, "invalid_provider_response", "D 返回的报告会话或模式不一致")
    report = Report(session_id=training.id, payload_json=validated.model_dump())
    training.status = "completed"
    training.completed_at = utc_now()
    if interview is not None:
        interview.status = "completed"
    db.add(report)
    db.commit()
    return validated


@router.get("/{session_id}", response_model=ReportResponse)
def get_report(
    session_id: str,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> ReportResponse:
    owned_training_session(session_id, db, token)
    report = db.scalar(select(Report).where(Report.session_id == session_id))
    if report is None:
        raise not_found("报告")
    return ReportResponse.model_validate(report.payload_json)
