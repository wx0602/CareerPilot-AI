"""add favorite questions

Revision ID: 20260714_0002
Revises: 20260714_0001
Create Date: 2026-07-14
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260714_0002"
down_revision: str | None = "20260714_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorite_questions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_key", sa.String(length=80), nullable=False),
        sa.Column("question_id", sa.String(length=100), nullable=False),
        sa.Column("question_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_key", "question_id", name="uq_favorite_owner_question"),
    )
    op.create_index("ix_favorite_questions_owner_key", "favorite_questions", ["owner_key"])
    op.create_index("ix_favorite_questions_question_id", "favorite_questions", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_favorite_questions_question_id", table_name="favorite_questions")
    op.drop_index("ix_favorite_questions_owner_key", table_name="favorite_questions")
    op.drop_table("favorite_questions")
