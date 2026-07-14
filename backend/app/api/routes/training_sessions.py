from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_token, get_db, owned_training_session
from app.core.errors import conflict
from app.dbmodels import AuthToken, TrainingSession
from app.schemas.api import TrainingSessionCreate, TrainingSessionResponse, TrainingSessionUpdate
from app.services.learning_modules import default_question_mix, get_learning_module


router = APIRouter(prefix="/training-sessions", tags=["训练会话"])


@router.post("", response_model=TrainingSessionResponse, status_code=status.HTTP_201_CREATED)
def create_training_session(
    payload: TrainingSessionCreate,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> TrainingSessionResponse:
    if token.is_guest:
        existing_count = db.scalar(
            select(func.count(TrainingSession.id)).where(
                TrainingSession.created_by_token_id == token.id
            )
        )
        if existing_count:
            raise conflict("guest_session_limit", "游客只能创建一个训练会话")
    module = get_learning_module(payload.learning_module)
    question_mix = payload.question_mix or (default_question_mix() if module else None)
    resolved_position = payload.position.strip() if payload.position else None
    if module and not resolved_position:
        resolved_position = module.default_position
    training = TrainingSession(
        owner_user_id=token.user_id,
        created_by_token_id=token.id,
        mode=payload.mode,
        position=resolved_position,
        company=payload.company.strip() if payload.company else None,
        learning_module=module.module_id if module else payload.learning_module,
        learning_module_title=(
            payload.learning_module_title.strip()
            if payload.learning_module_title
            else (module.title if module else None)
        ),
        question_mix=question_mix.model_dump() if question_mix else None,
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return TrainingSessionResponse(
        session_id=training.id,
        mode=training.mode,
        position=training.position,
        company=training.company,
        learning_module=training.learning_module,
        learning_module_title=training.learning_module_title,
        question_mix=training.question_mix,
        status=training.status,
        created_at=training.created_at,
    )


@router.patch("/{session_id}", response_model=TrainingSessionResponse)
def update_training_session(
    session_id: str,
    payload: TrainingSessionUpdate,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> TrainingSessionResponse:
    training = owned_training_session(session_id, db, token)
    module = get_learning_module(payload.learning_module) if payload.learning_module else None
    if payload.position is not None:
        training.position = payload.position.strip() if payload.position else None
    elif module and not training.position:
        training.position = module.default_position
    if payload.company is not None:
        training.company = payload.company.strip() if payload.company else None
    if payload.learning_module is not None:
        training.learning_module = module.module_id if module else payload.learning_module
    if payload.learning_module_title is not None:
        training.learning_module_title = (
            payload.learning_module_title.strip() if payload.learning_module_title else None
        )
    elif module:
        training.learning_module_title = module.title
    if payload.question_mix is not None:
        training.question_mix = payload.question_mix.model_dump()
    elif module and training.question_mix is None:
        training.question_mix = default_question_mix().model_dump()
    db.add(training)
    db.commit()
    db.refresh(training)
    return TrainingSessionResponse(
        session_id=training.id,
        mode=training.mode,
        position=training.position,
        company=training.company,
        learning_module=training.learning_module,
        learning_module_title=training.learning_module_title,
        question_mix=training.question_mix,
        status=training.status,
        created_at=training.created_at,
    )
