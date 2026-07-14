from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.security import utc_now
from ..db.base import Base


def uuid_str() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    account: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User | None] = relationship()


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_by_token_id: Mapped[str] = mapped_column(ForeignKey("auth_tokens.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20), index=True)
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)
    company: Mapped[str | None] = mapped_column(String(120), nullable=True)
    learning_module: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    learning_module_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    question_mix: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("training_sessions.id"), index=True)
    material_type: Mapped[str] = mapped_column(String(20))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")
    contexts_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (UniqueConstraint("session_id", name="uq_exams_session_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("training_sessions.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    questions: Mapped[list["ExamQuestion"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.ordinal"
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), index=True)
    question_id: Mapped[str] = mapped_column(String(100))
    ordinal: Mapped[int] = mapped_column(Integer)
    public_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    grading_payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    exam: Mapped[Exam] = relationship(back_populates="questions")


class ExamSubmission(Base):
    __tablename__ = "exam_submissions"
    __table_args__ = (UniqueConstraint("exam_id", name="uq_exam_submissions_exam_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), index=True)
    answer_hash: Mapped[str] = mapped_column(String(64))
    answers_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (UniqueConstraint("session_id", name="uq_interviews_session_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("training_sessions.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class InterviewTurn(Base):
    __tablename__ = "interview_turns"
    __table_args__ = (
        UniqueConstraint("interview_id", "ordinal", name="uq_interview_turn_ordinal"),
        UniqueConstraint("interview_id", "question_id", name="uq_interview_turn_question"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    interview_id: Mapped[str] = mapped_column(ForeignKey("interviews.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    question_id: Mapped[str] = mapped_column(String(100))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("session_id", name="uq_reports_session_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    session_id: Mapped[str] = mapped_column(ForeignKey("training_sessions.id"), index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FavoriteQuestion(Base):
    __tablename__ = "favorite_questions"
    __table_args__ = (
        UniqueConstraint("owner_key", "question_id", name="uq_favorite_owner_question"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    owner_key: Mapped[str] = mapped_column(String(80), index=True)
    question_id: Mapped[str] = mapped_column(String(100), index=True)
    question_type: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
