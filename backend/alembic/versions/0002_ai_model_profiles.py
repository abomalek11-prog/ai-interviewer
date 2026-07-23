"""add ai model profile selection

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("ai_model_profile_id", sa.String(length=80), nullable=True))
    op.add_column("interview_sessions", sa.Column("ai_model_profile_id", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("interview_sessions", "ai_model_profile_id")
    op.drop_column("jobs", "ai_model_profile_id")
