"""add user profile fields

Revision ID: 20260717_0004
Revises: 20260714_0003
Create Date: 2026-07-17
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260717_0004"
down_revision: str | None = "20260714_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("nickname", sa.String(length=20), nullable=True))
    op.add_column(
        "users",
        sa.Column("avatar_preset", sa.String(length=20), nullable=False, server_default="blue"),
    )
    op.add_column("users", sa.Column("target_position", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("career_stage", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "career_stage")
    op.drop_column("users", "target_position")
    op.drop_column("users", "avatar_preset")
    op.drop_column("users", "nickname")
