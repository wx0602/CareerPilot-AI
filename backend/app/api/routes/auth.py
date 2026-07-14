from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_token, get_db
from app.core.errors import unauthorized
from app.core.security import (
    hash_access_token,
    new_access_token,
    utc_now,
    verify_password,
)
from app.dbmodels import AuthToken, User
from app.schemas.api import AuthResponse, LoginRequest, UserInfo


router = APIRouter(prefix="/auth", tags=["认证"])


def _issue_token(
    db: Session,
    *,
    user: User | None,
    is_guest: bool,
    expires_at,
) -> AuthResponse:
    raw_token = new_access_token()
    record = AuthToken(
        token_hash=hash_access_token(raw_token),
        user_id=user.id if user else None,
        is_guest=is_guest,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    return AuthResponse(
        access_token=raw_token,
        expires_at=expires_at,
        user=UserInfo(
            user_id=user.id if user else None,
            account=user.account if user else None,
            is_guest=is_guest,
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    account = payload.account.strip().lower()
    user = db.scalar(select(User).where(User.account == account))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise unauthorized("账号或密码错误")
    settings = request.app.state.settings
    duration = (
        timedelta(days=settings.remember_token_ttl_days)
        if payload.remember_me
        else timedelta(hours=settings.auth_token_ttl_hours)
    )
    return _issue_token(db, user=user, is_guest=False, expires_at=utc_now() + duration)


@router.post("/guest", response_model=AuthResponse)
def guest(request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    settings = request.app.state.settings
    return _issue_token(
        db,
        user=None,
        is_guest=True,
        expires_at=utc_now() + timedelta(hours=settings.guest_token_ttl_hours),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> Response:
    token.revoked_at = utc_now()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
