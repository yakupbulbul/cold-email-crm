"""add mailbox smtp mode and diagnostics

Revision ID: d1a7c2f9b410
Revises: f58f5b5d6a10
Create Date: 2026-04-09 02:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d1a7c2f9b410"
down_revision = "f58f5b5d6a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mailboxes", sa.Column("smtp_security_mode", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("smtp_last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("mailboxes", sa.Column("smtp_last_check_status", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("smtp_last_check_category", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("smtp_last_check_message", sa.String(), nullable=True))

    op.execute(
        """
        UPDATE mailboxes
        SET smtp_security_mode = CASE
            WHEN smtp_port = 465 THEN 'ssl'
            ELSE 'starttls'
        END
        WHERE smtp_security_mode IS NULL
        """
    )
    op.alter_column("mailboxes", "smtp_security_mode", nullable=False, server_default="starttls")


def downgrade() -> None:
    op.drop_column("mailboxes", "smtp_last_check_message")
    op.drop_column("mailboxes", "smtp_last_check_category")
    op.drop_column("mailboxes", "smtp_last_check_status")
    op.drop_column("mailboxes", "smtp_last_checked_at")
    op.drop_column("mailboxes", "smtp_security_mode")
