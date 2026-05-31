"""Drop Mailcow columns and AI summaries table

Revision ID: a1b2c3d4e5f6
Revises: e6c4aa7a9c11
Create Date: 2026-05-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e6c4aa7a9c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Drop Mailcow columns from domains ---
    op.drop_column("domains", "mailcow_status")
    op.drop_column("domains", "mailcow_detail")
    op.drop_column("domains", "mailcow_last_checked_at")

    # --- Drop Mailcow provisioning flag from mailboxes ---
    op.drop_column("mailboxes", "remote_mailcow_provisioned")

    # --- Drop Mailcow columns from mail_provider_settings ---
    op.drop_column("mail_provider_settings", "mailcow_enabled")
    op.drop_column("mail_provider_settings", "mailcow_last_checked_at")
    op.drop_column("mail_provider_settings", "mailcow_last_check_status")
    op.drop_column("mail_provider_settings", "mailcow_last_check_message")

    # --- Update existing rows: set provider defaults to google_workspace ---
    op.execute("UPDATE mailboxes SET provider_type = 'google_workspace' WHERE provider_type = 'mailcow'")
    op.execute("UPDATE mail_provider_settings SET default_provider = 'google_workspace' WHERE default_provider = 'mailcow'")

    # --- Drop AI summaries table ---
    op.drop_table("ai_summaries")


def downgrade() -> None:
    # --- Restore AI summaries table ---
    op.create_table(
        "ai_summaries",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["threads.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Restore Mailcow columns on mail_provider_settings ---
    op.add_column("mail_provider_settings", sa.Column("mailcow_last_check_message", sa.String(), nullable=True))
    op.add_column("mail_provider_settings", sa.Column("mailcow_last_check_status", sa.String(), nullable=True))
    op.add_column("mail_provider_settings", sa.Column("mailcow_last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("mail_provider_settings", sa.Column("mailcow_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    # --- Restore Mailcow provisioning flag on mailboxes ---
    op.add_column("mailboxes", sa.Column("remote_mailcow_provisioned", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # --- Restore Mailcow columns on domains ---
    op.add_column("domains", sa.Column("mailcow_last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("domains", sa.Column("mailcow_detail", sa.String(), nullable=True))
    op.add_column("domains", sa.Column("mailcow_status", sa.String(), nullable=True))
