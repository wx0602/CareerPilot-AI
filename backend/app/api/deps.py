from collections.abc import Generator
from datetime import timezone

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.errors import forbidden, not_found, unauthorized
from ..core.security import hash_access_token, utc_now
from ..dbmodels import AuthToken, TrainingSession


bearer_scheme = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthToken:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    token = db.scalar(
        select(AuthToken).where(AuthToken.token_hash == hash_access_token(credentials.credentials))
    )
    if token is None or token.revoked_at is not None:
        raise unauthorized()
    expires_at = token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= utc_now():
        raise unauthorized()
    return token


def owned_training_session(
    session_id: str,
    db: Session,
    token: AuthToken,
) -> TrainingSession:
    training = db.get(TrainingSession, session_id)
    if training is None:
        raise not_found("训练会话")
    if token.is_guest:
        if training.created_by_token_id != token.id:
            raise forbidden()
    elif training.owner_user_id != token.user_id:
        raise forbidden()
    return training
