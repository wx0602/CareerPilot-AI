"""create phase-one backend schema

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260714_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("account", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_account", "users", ["account"], unique=True)

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("is_guest", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"], unique=True)
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"], unique=False)

    op.create_table(
        "training_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_token_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("position", sa.String(length=120), nullable=True),
        sa.Column("company", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_token_id"], ["auth_tokens.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_training_sessions_created_by_token_id",
        "training_sessions",
        ["created_by_token_id"],
        unique=False,
    )
    op.create_index("ix_training_sessions_mode", "training_sessions", ["mode"], unique=False)
    op.create_index(
        "ix_training_sessions_owner_user_id",
        "training_sessions",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "materials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("material_type", sa.String(length=20), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("parse_status", sa.String(length=20), nullable=False),
        sa.Column("contexts_json", sa.JSON(), nullable=False),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_materials_session_id", "materials", ["session_id"], unique=False)

    op.create_table(
        "exams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_exams_session_id"),
    )
    op.create_index("ix_exams_session_id", "exams", ["session_id"], unique=False)

    op.create_table(
        "exam_questions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("exam_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=100), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("public_payload", sa.JSON(), nullable=False),
        sa.Column("grading_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
    )
    op.create_index("ix_exam_questions_exam_id", "exam_questions", ["exam_id"], unique=False)

    op.create_table(
        "exam_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("exam_id", sa.String(length=36), nullable=False),
        sa.Column("answer_hash", sa.String(length=64), nullable=False),
        sa.Column("answers_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", name="uq_exam_submissions_exam_id"),
    )
    op.create_index(
        "ix_exam_submissions_exam_id", "exam_submissions", ["exam_id"], unique=False
    )

    op.create_table(
        "interviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_interviews_session_id"),
    )
    op.create_index("ix_interviews_session_id", "interviews", ["session_id"], unique=False)

    op.create_table(
        "interview_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("interview_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(length=100), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("evaluation_json", sa.JSON(), nullable=True),
        sa.Column("is_followup", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id", "ordinal", name="uq_interview_turn_ordinal"),
        sa.UniqueConstraint(
            "interview_id", "question_id", name="uq_interview_turn_question"
        ),
    )
    op.create_index(
        "ix_interview_turns_interview_id",
        "interview_turns",
        ["interview_id"],
        unique=False,
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_reports_session_id"),
    )
    op.create_index("ix_reports_session_id", "reports", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("interview_turns")
    op.drop_table("interviews")
    op.drop_table("exam_submissions")
    op.drop_table("exam_questions")
    op.drop_table("exams")
    op.drop_table("materials")
    op.drop_table("training_sessions")
    op.drop_table("auth_tokens")
    op.drop_table("users")
