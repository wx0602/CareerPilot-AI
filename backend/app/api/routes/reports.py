from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_token, get_db, owned_training_session
from ...core.errors import api_error, conflict, not_found
from ...core.security import utc_now
from ...dbmodels import (
    AuthToken,
    Exam,
    ExamSubmission,
    Interview,
    InterviewTurn,
    Report,
    TrainingSession,
)
from ...schemas.api import ReportGenerateRequest, ReportListItem, ReportResponse
from ...services.providers import ProviderUnavailableError


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
    if payload.nonverbal_score is not None and training.mode == "job":
        validated = validated.model_copy(update={"nonverbal_score": payload.nonverbal_score})
    report = Report(session_id=training.id, payload_json=validated.model_dump())
    training.status = "completed"
    training.completed_at = utc_now()
    if interview is not None:
        interview.status = "completed"
    db.add(report)
    db.commit()
    return validated


@router.get("", response_model=list[ReportListItem])
def list_reports(
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> list[ReportListItem]:
    statement = (
        select(Report, TrainingSession)
        .join(TrainingSession, TrainingSession.id == Report.session_id)
        .order_by(Report.generated_at.desc())
    )
    if token.is_guest:
        statement = statement.where(TrainingSession.created_by_token_id == token.id)
    else:
        statement = statement.where(TrainingSession.owner_user_id == token.user_id)

    items: list[ReportListItem] = []
    for report, training in db.execute(statement).all():
        payload = ReportResponse.model_validate(report.payload_json)
        items.append(
            ReportListItem(
                **payload.model_dump(),
                generated_at=report.generated_at,
                position=training.position,
                company=training.company,
                learning_module_title=training.learning_module_title,
            )
        )
    return items


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
