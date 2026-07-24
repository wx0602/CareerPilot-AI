"""add indexes for history and material queries

Revision ID: 20260724_0005
Revises: 20260717_0004
Create Date: 2026-07-24
"""

from typing import Sequence

from alembic import op


revision: str = "20260724_0005"
down_revision: str | None = "20260717_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_training_sessions_owner_created",
        "training_sessions",
        ["owner_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_training_sessions_token_created",
        "training_sessions",
        ["created_by_token_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_materials_session_type",
        "materials",
        ["session_id", "material_type"],
        unique=False,
    )
    op.create_index(
        "ix_reports_generated_at",
        "reports",
        ["generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reports_generated_at", table_name="reports")
    op.drop_index("ix_materials_session_type", table_name="materials")
    op.drop_index("ix_training_sessions_token_created", table_name="training_sessions")
    op.drop_index("ix_training_sessions_owner_created", table_name="training_sessions")
