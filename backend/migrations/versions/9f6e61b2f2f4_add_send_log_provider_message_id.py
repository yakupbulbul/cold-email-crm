"""add provider message id to send logs

Revision ID: 9f6e61b2f2f4
Revises: d1a7c2f9b410
Create Date: 2026-04-09 02:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "9f6e61b2f2f4"
down_revision = "d1a7c2f9b410"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("send_logs", sa.Column("provider_message_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("send_logs", "provider_message_id")
