"""add notification read states

Revision ID: afe91c2d7b30
Revises: c7d8e9f0a1b2
Create Date: 2026-04-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "afe91c2d7b30"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_read_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_key", sa.String(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "notification_key", name="uq_notification_read_states_user_key"),
    )
    op.create_index(op.f("ix_notification_read_states_notification_key"), "notification_read_states", ["notification_key"], unique=False)
    op.create_index(op.f("ix_notification_read_states_user_id"), "notification_read_states", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_read_states_user_id"), table_name="notification_read_states")
    op.drop_index(op.f("ix_notification_read_states_notification_key"), table_name="notification_read_states")
    op.drop_table("notification_read_states")

