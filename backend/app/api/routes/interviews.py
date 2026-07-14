from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_token, get_db, owned_training_session
from ...core.errors import api_error, conflict, not_found
from ...core.security import utc_now
from ...dbmodels import AuthToken, Interview, InterviewTurn, Material
from ...schemas.api import (
    EvaluationResponse,
    InterviewMessageRequest,
    InterviewMessageResponse,
    QuestionResponse,
)
from ...services.providers import ProviderUnavailableError


router = APIRouter(prefix="/interviews", tags=["文本面试"])


def _turns(db: Session, interview_id: str) -> list[InterviewTurn]:
    return list(
        db.scalars(
            select(InterviewTurn)
            .where(InterviewTurn.interview_id == interview_id)
            .order_by(InterviewTurn.ordinal)
        )
    )


def _provider_question_request(training, materials, turns) -> dict:
    contexts = [chunk for material in materials for chunk in (material.contexts_json or [])]
    history = [
        {"question_id": turn.question_id, "question": turn.question, "answer": turn.answer}
        for turn in turns
    ]
    return {
        "session_id": training.id,
        "mode": training.mode,
        "candidate_profile": {
            "name": None,
            "target_position": training.position,
            "target_company": training.company,
        },
        "contexts": contexts,
        "history": history,
    }


@router.post("/message", response_model=InterviewMessageResponse)
def interview_message(
    payload: InterviewMessageRequest,
    request: Request,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> InterviewMessageResponse:
    training = owned_training_session(payload.session_id, db, token)
    interview = db.scalar(select(Interview).where(Interview.session_id == training.id))
    if interview is None:
        interview = Interview(session_id=training.id, mode=training.mode, status="active")
        db.add(interview)
        db.flush()
    turns = _turns(db, interview.id)
    materials = list(db.scalars(select(Material).where(Material.session_id == training.id)))

    if payload.question_id is None:
        if turns:
            current = turns[-1]
            return InterviewMessageResponse(
                interview_id=interview.id,
                next_question=QuestionResponse(
                    question_id=current.question_id,
                    question=current.question,
                ),
                is_followup=current.is_followup,
            )
        try:
            generated = request.app.state.ai_provider.generate_question(
                _provider_question_request(training, materials, turns)
            )
        except ProviderUnavailableError as exc:
            raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
        question = QuestionResponse.model_validate(generated)
        first_turn = InterviewTurn(
            interview_id=interview.id,
            ordinal=1,
            question_id=question.question_id,
            question=question.question,
        )
        training.status = "active"
        db.add(first_turn)
        db.commit()
        return InterviewMessageResponse(interview_id=interview.id, next_question=question)

    turn = next((item for item in turns if item.question_id == payload.question_id), None)
    if turn is None:
        raise not_found("面试问题")
    answer = payload.answer.strip()
    if turn.answer is not None:
        if turn.answer != answer:
            raise conflict("question_already_answered", "该问题已经回答，不能修改答案")
        next_turn = next((item for item in turns if item.ordinal == turn.ordinal + 1), None)
        if next_turn is None:
            raise conflict("interview_state_invalid", "已回答问题缺少后续问题")
        return InterviewMessageResponse(
            interview_id=interview.id,
            evaluation=EvaluationResponse.model_validate(turn.evaluation_json),
            next_question=QuestionResponse(
                question_id=next_turn.question_id,
                question=next_turn.question,
            ),
            is_followup=next_turn.is_followup,
        )
    if turns[-1].id != turn.id:
        raise conflict("out_of_order_answer", "只能回答当前最新问题")

    evaluation_request = {
        "session_id": training.id,
        "mode": training.mode,
        "question_id": turn.question_id,
        "question": turn.question,
        "answer": answer,
    }
    try:
        evaluation_data = request.app.state.ai_provider.evaluate_answer(evaluation_request)
    except ProviderUnavailableError as exc:
        raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
    evaluation = EvaluationResponse.model_validate(evaluation_data)
    if evaluation.question_id != turn.question_id:
        raise api_error(502, "invalid_provider_response", "D 返回的 question_id 与请求不一致")
    turn.answer = answer
    turn.evaluation_json = evaluation.model_dump()
    turn.answered_at = utc_now()

    if evaluation.need_followup and evaluation.followup_question:
        next_question = QuestionResponse(
            question_id=str(uuid4()),
            question=evaluation.followup_question,
        )
        is_followup = True
    else:
        history_with_answer = turns
        try:
            generated = request.app.state.ai_provider.generate_question(
                _provider_question_request(training, materials, history_with_answer)
            )
        except ProviderUnavailableError as exc:
            raise api_error(503, "ai_provider_unavailable", str(exc)) from exc
        next_question = QuestionResponse.model_validate(generated)
        is_followup = False

    db.add(
        InterviewTurn(
            interview_id=interview.id,
            ordinal=turn.ordinal + 1,
            question_id=next_question.question_id,
            question=next_question.question,
            is_followup=is_followup,
        )
    )
    db.commit()
    return InterviewMessageResponse(
        interview_id=interview.id,
        evaluation=evaluation,
        next_question=next_question,
        is_followup=is_followup,
    )
