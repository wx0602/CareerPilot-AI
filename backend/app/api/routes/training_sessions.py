from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_token, get_db
from app.core.errors import conflict
from app.dbmodels import AuthToken, TrainingSession
from app.schemas.api import TrainingSessionCreate, TrainingSessionResponse


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
    training = TrainingSession(
        owner_user_id=token.user_id,
        created_by_token_id=token.id,
        mode=payload.mode,
        position=payload.position.strip() if payload.position else None,
        company=payload.company.strip() if payload.company else None,
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return TrainingSessionResponse(
        session_id=training.id,
        mode=training.mode,
        position=training.position,
        company=training.company,
        status=training.status,
        created_at=training.created_at,
    )
