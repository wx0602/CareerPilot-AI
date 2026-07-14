import json
from hashlib import sha256

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_token, get_db, owned_training_session
from app.core.errors import api_error, conflict, not_found
from app.core.security import utc_now
from app.dbmodels import AuthToken, Exam, ExamQuestion, ExamSubmission
from app.schemas.api import (
    ExamPaperResponse,
    ExamResultResponse,
    ExamSubmissionRequest,
    GenerateExamRequest,
)
from app.services.providers import ProviderUnavailableError


router = APIRouter(prefix="/exams", tags=["笔试"])


def _paper_from_exam(exam: Exam) -> ExamPaperResponse:
    return ExamPaperResponse(
        exam_id=exam.id,
        session_id=exam.session_id,
        title=exam.title,
        questions=[item.public_payload for item in exam.questions],
    )


def _canonical_answer_hash(payload: ExamSubmissionRequest) -> str:
    normalized = []
    for item in sorted(payload.answers, key=lambda value: value.question_id):
        answer = sorted(item.answer) if isinstance(item.answer, list) else item.answer
        normalized.append({"question_id": item.question_id, "answer": answer})
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(raw.encode("utf-8")).hexdigest()


@router.post("/generate", response_model=ExamPaperResponse)
def generate_exam(
    payload: GenerateExamRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> ExamPaperResponse:
    training = owned_training_session(payload.session_id, db, token)
    existing = db.scalar(
        select(Exam)
        .options(selectinload(Exam.questions))
        .where(Exam.session_id == payload.session_id)
    )
    if existing is not None:
        return _paper_from_exam(existing)
    try:
        paper, grading_items = request.app.state.ai_provider.generate_exam(payload.model_dump())
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    validated = ExamPaperResponse.model_validate(paper)
    if validated.session_id != payload.session_id:
        raise api_error(502, "invalid_provider_response", "D 返回的 session_id 与请求不一致")
    if len(validated.questions) != len(grading_items):
        raise api_error(502, "invalid_provider_response", "公开题目与私有评分题目数量不一致")

    grading_by_id = {item["question_id"]: item for item in grading_items}
    exam = Exam(
        id=validated.exam_id,
        session_id=payload.session_id,
        title=validated.title,
        difficulty=payload.difficulty,
        status="generated",
    )
    for ordinal, public_question in enumerate(validated.questions, start=1):
        grading_item = grading_by_id.get(public_question.question_id)
        if grading_item is None:
            raise api_error(502, "invalid_provider_response", "D 未返回完整评分上下文")
        exam.questions.append(
            ExamQuestion(
                question_id=public_question.question_id,
                ordinal=ordinal,
                public_payload=public_question.model_dump(),
                grading_payload=grading_item,
            )
        )
    training.position = payload.position
    training.company = payload.company
    training.status = "active"
    db.add(exam)
    db.commit()
    return _paper_from_exam(exam)


@router.post("/submit", response_model=ExamResultResponse)
def submit_exam(
    payload: ExamSubmissionRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> ExamResultResponse:
    owned_training_session(payload.session_id, db, token)
    exam = db.scalar(
        select(Exam).options(selectinload(Exam.questions)).where(Exam.id == payload.exam_id)
    )
    if exam is None:
        raise not_found("试卷")
    if exam.session_id != payload.session_id:
        raise conflict("session_mismatch", "试卷不属于指定训练会话")

    answer_hash = _canonical_answer_hash(payload)
    existing = db.scalar(select(ExamSubmission).where(ExamSubmission.exam_id == exam.id))
    if existing is not None:
        if existing.answer_hash == answer_hash:
            return ExamResultResponse.model_validate(existing.result_json)
        raise conflict("exam_already_submitted", "该试卷已经提交，不能修改答案")

    answer_ids = [item.question_id for item in payload.answers]
    if len(answer_ids) != len(set(answer_ids)):
        raise api_error(422, "duplicate_answer", "同一道题不能提交多份答案")
    valid_ids = {item.question_id for item in exam.questions}
    unknown_ids = sorted(set(answer_ids) - valid_ids)
    if unknown_ids:
        raise api_error(422, "unknown_question", f"试卷中不存在题目：{', '.join(unknown_ids)}")

    provider_payload = payload.model_dump()
    grading_items = [item.grading_payload for item in exam.questions]
    try:
        result = request.app.state.ai_provider.grade_exam(provider_payload, grading_items)
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    validated = ExamResultResponse.model_validate(result)
    if validated.exam_id != exam.id:
        raise api_error(502, "invalid_provider_response", "D 返回的 exam_id 与请求不一致")
    submission = ExamSubmission(
        exam_id=exam.id,
        answer_hash=answer_hash,
        answers_json=[item.model_dump() for item in payload.answers],
        result_json=validated.model_dump(),
    )
    exam.status = "submitted"
    db.add(submission)
    db.commit()
    return validated


@router.get("/{exam_id}/result", response_model=ExamResultResponse)
def get_exam_result(
    exam_id: str,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> ExamResultResponse:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise not_found("试卷")
    owned_training_session(exam.session_id, db, token)
    submission = db.scalar(select(ExamSubmission).where(ExamSubmission.exam_id == exam_id))
    if submission is None:
        raise not_found("笔试结果")
    return ExamResultResponse.model_validate(submission.result_json)
