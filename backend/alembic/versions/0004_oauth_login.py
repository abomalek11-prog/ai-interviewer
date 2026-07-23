"""add oauth login support

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("hashed_password", existing_type=sa.String(length=255), nullable=True)
        batch_op.add_column(sa.Column("oauth_provider", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("oauth_id", sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint("uq_users_oauth_identity", ["oauth_provider", "oauth_id"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_oauth_identity", type_="unique")
        batch_op.drop_column("oauth_id")
        batch_op.drop_column("oauth_provider")
        batch_op.alter_column("hashed_password", existing_type=sa.String(length=255), nullable=False)
