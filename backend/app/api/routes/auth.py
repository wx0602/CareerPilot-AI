from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..deps import get_current_token, get_db
from ...core.errors import api_error, conflict, forbidden, unauthorized
from ...core.security import (
    hash_access_token,
    hash_password,
    new_access_token,
    utc_now,
    verify_password,
)
from ...dbmodels import (
    AuthToken,
    Exam,
    ExamSubmission,
    FavoriteQuestion,
    Interview,
    InterviewTurn,
    Report,
    TrainingSession,
    User,
)
from ...schemas.api import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserInfo,
    UserProfileResponse,
    UserProfileStats,
    UserProfileUpdate,
)


router = APIRouter(prefix="/auth", tags=["认证"])


def _user_info(user: User | None, *, is_guest: bool) -> UserInfo:
    return UserInfo(
        user_id=user.id if user else None,
        account=user.account if user else None,
        is_guest=is_guest,
        nickname=user.nickname if user else None,
        avatar_preset=user.avatar_preset if user else "blue",
        target_position=user.target_position if user else None,
        career_stage=user.career_stage if user else None,
        created_at=user.created_at if user else None,
    )


def _owner_condition(token: AuthToken):
    if token.is_guest:
        return TrainingSession.created_by_token_id == token.id
    return TrainingSession.owner_user_id == token.user_id


def _profile_response(db: Session, token: AuthToken) -> UserProfileResponse:
    user = db.get(User, token.user_id) if token.user_id else None
    owner_condition = _owner_condition(token)

    exam_session_ids = set(
        db.scalars(
            select(Exam.session_id)
            .join(ExamSubmission, ExamSubmission.exam_id == Exam.id)
            .join(TrainingSession, TrainingSession.id == Exam.session_id)
            .where(owner_condition)
        )
    )
    interview_session_ids = set(
        db.scalars(
            select(Interview.session_id)
            .join(TrainingSession, TrainingSession.id == Interview.session_id)
            .where(owner_condition, Interview.status == "completed")
        )
    )
    answer_payloads = db.scalars(
        select(ExamSubmission.answers_json)
        .join(Exam, Exam.id == ExamSubmission.exam_id)
        .join(TrainingSession, TrainingSession.id == Exam.session_id)
        .where(owner_condition)
    )
    interview_answer_count = db.scalar(
        select(func.count(InterviewTurn.id))
        .join(Interview, Interview.id == InterviewTurn.interview_id)
        .join(TrainingSession, TrainingSession.id == Interview.session_id)
        .where(owner_condition, InterviewTurn.answer.is_not(None))
    ) or 0
    report_count = db.scalar(
        select(func.count(Report.id))
        .join(TrainingSession, TrainingSession.id == Report.session_id)
        .where(owner_condition)
    ) or 0
    owner_key = f"guest:{token.id}" if token.is_guest else f"user:{token.user_id}"
    favorite_count = db.scalar(
        select(func.count(FavoriteQuestion.id)).where(FavoriteQuestion.owner_key == owner_key)
    ) or 0
    last_study_at = db.scalar(
        select(func.max(TrainingSession.updated_at)).where(owner_condition)
    )

    return UserProfileResponse(
        user=_user_info(user, is_guest=token.is_guest),
        stats=UserProfileStats(
            completed_practices=len(exam_session_ids | interview_session_ids),
            answered_questions=sum(len(items or []) for items in answer_payloads)
            + interview_answer_count,
            favorite_questions=favorite_count,
            report_count=report_count,
            last_study_at=last_study_at,
        ),
    )


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
        user=_user_info(user, is_guest=is_guest),
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


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    account = payload.account.strip().lower()
    if db.scalar(select(User).where(User.account == account)) is not None:
        raise conflict("account_exists", "该账号已注册")
    user = User(account=account, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    return _issue_token(
        db,
        user=user,
        is_guest=False,
        expires_at=utc_now() + timedelta(hours=request.app.state.settings.auth_token_ttl_hours),
    )


@router.post("/guest", response_model=AuthResponse)
def guest(request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    settings = request.app.state.settings
    return _issue_token(
        db,
        user=None,
        is_guest=True,
        expires_at=utc_now() + timedelta(hours=settings.guest_token_ttl_hours),
    )


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    return _profile_response(db, token)


@router.patch("/me", response_model=UserProfileResponse)
def update_my_profile(
    payload: UserProfileUpdate,
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    if token.is_guest or token.user_id is None:
        raise forbidden("游客账号注册后才能保存个人资料")
    user = db.get(User, token.user_id)
    if user is None:
        raise unauthorized()
    nickname = payload.nickname.strip()
    if len(nickname) < 2:
        raise api_error(422, "invalid_nickname", "昵称至少需要 2 个字符")
    user.nickname = nickname
    user.avatar_preset = payload.avatar_preset
    user.target_position = payload.target_position.strip() if payload.target_position else None
    user.career_stage = payload.career_stage
    db.commit()
    db.refresh(user)
    return _profile_response(db, token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: AuthToken = Depends(get_current_token),
    db: Session = Depends(get_db),
) -> Response:
    token.revoked_at = utc_now()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
