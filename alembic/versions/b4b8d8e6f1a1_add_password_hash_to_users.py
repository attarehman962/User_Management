"""add password hash to users

Revision ID: b4b8d8e6f1a1
Revises: a678bc6365f8
Create Date: 2026-04-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4b8d8e6f1a1"
down_revision: Union[str, Sequence[str], None] = "a678bc6365f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("users", "password_hash", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "password_hash")
