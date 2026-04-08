"""add mailbox provisioning flag

Revision ID: c4f9f2d8d120
Revises: b2d9c4e4a001
Create Date: 2026-04-08 23:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c4f9f2d8d120"
down_revision = "b2d9c4e4a001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mailboxes",
        sa.Column("remote_mailcow_provisioned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("mailboxes", "remote_mailcow_provisioned", server_default=None)


def downgrade() -> None:
    op.drop_column("mailboxes", "remote_mailcow_provisioned")
