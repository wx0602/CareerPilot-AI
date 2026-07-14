from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_token, get_db
from app.dbmodels import AuthToken, FavoriteQuestion
from app.schemas.api import FavoriteQuestionCreate, FavoriteQuestionResponse


router = APIRouter(prefix="/favorites", tags=["收藏题库"])


def _owner_key(token: AuthToken) -> str:
    if token.is_guest:
        return f"guest:{token.id}"
    return f"user:{token.user_id}"


def _to_response(row: FavoriteQuestion) -> FavoriteQuestionResponse:
    return FavoriteQuestionResponse(
        favorite_id=row.id,
        question_id=row.question_id,
        question_type=row.question_type,
        content=row.content,
        question=row.payload_json,
        created_at=row.created_at,
    )


@router.get("", response_model=list[FavoriteQuestionResponse])
def list_favorites(
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> list[FavoriteQuestionResponse]:
    rows = db.scalars(
        select(FavoriteQuestion)
        .where(FavoriteQuestion.owner_key == _owner_key(token))
        .order_by(FavoriteQuestion.created_at.desc())
    )
    return [_to_response(row) for row in rows]


@router.post("", response_model=FavoriteQuestionResponse, status_code=status.HTTP_201_CREATED)
def add_favorite(
    payload: FavoriteQuestionCreate,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> FavoriteQuestionResponse:
    owner = _owner_key(token)
    existing = db.scalar(
        select(FavoriteQuestion).where(
            FavoriteQuestion.owner_key == owner,
            FavoriteQuestion.question_id == payload.question.question_id,
        )
    )
    if existing is not None:
        return _to_response(existing)

    row = FavoriteQuestion(
        owner_key=owner,
        question_id=payload.question.question_id,
        question_type=payload.question.question_type,
        content=payload.question.content,
        payload_json=payload.question.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite(
    question_id: str,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> None:
    db.execute(
        delete(FavoriteQuestion).where(
            FavoriteQuestion.owner_key == _owner_key(token),
            FavoriteQuestion.question_id == question_id,
        )
    )
    db.commit()
