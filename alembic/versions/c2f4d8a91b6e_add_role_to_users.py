"""add role to users

Revision ID: c2f4d8a91b6e
Revises: b4b8d8e6f1a1
Create Date: 2026-05-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f4d8a91b6e"
down_revision: Union[str, Sequence[str], None] = "b4b8d8e6f1a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
    )
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")
