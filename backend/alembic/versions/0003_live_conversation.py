"""add live interview conversation mode

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="structured"),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversation_messages_session_id", "conversation_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_conversation_messages_session_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_column("interview_sessions", "mode")
