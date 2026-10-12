"""store the on-camera presence analysis of live interviews

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_evaluations", sa.Column("presence", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("session_evaluations") as batch_op:
        batch_op.drop_column("presence")
