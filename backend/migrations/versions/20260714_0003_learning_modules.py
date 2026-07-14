"""add learning module fields to training sessions

Revision ID: 20260714_0003
Revises: 20260714_0002
Create Date: 2026-07-14
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260714_0003"
down_revision: str | None = "20260714_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "training_sessions",
        sa.Column("learning_module", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "training_sessions",
        sa.Column("learning_module_title", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "training_sessions",
        sa.Column("question_mix", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_training_sessions_learning_module",
        "training_sessions",
        ["learning_module"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_training_sessions_learning_module", table_name="training_sessions")
    op.drop_column("training_sessions", "question_mix")
    op.drop_column("training_sessions", "learning_module_title")
    op.drop_column("training_sessions", "learning_module")
