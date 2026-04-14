"""add inbox sync and thread metadata

Revision ID: 18c4b6ee2f10
Revises: 4abf8d20c911
Create Date: 2026-04-14 23:55:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "18c4b6ee2f10"
down_revision = "4abf8d20c911"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mailboxes", sa.Column("inbox_sync_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("mailboxes", sa.Column("inbox_sync_status", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("inbox_last_synced_at", sa.DateTime(), nullable=True))
    op.add_column("mailboxes", sa.Column("inbox_last_success_at", sa.DateTime(), nullable=True))
    op.add_column("mailboxes", sa.Column("inbox_last_error", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("inbox_last_seen_uid", sa.String(), nullable=True))

    op.add_column("threads", sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("threads", sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("threads", sa.Column("contact_email", sa.String(), nullable=True))
    op.add_column("threads", sa.Column("linkage_status", sa.String(), nullable=False, server_default="unlinked"))
    op.create_index(op.f("ix_threads_contact_email"), "threads", ["contact_email"], unique=False)
    op.create_foreign_key("fk_threads_campaign_id", "threads", "campaigns", ["campaign_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_threads_contact_id", "threads", "contacts", ["contact_id"], ["id"], ondelete="SET NULL")

    op.add_column("messages", sa.Column("imap_uid", sa.String(), nullable=True))
    op.add_column("messages", sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_messages_imap_uid"), "messages", ["imap_uid"], unique=False)

    op.execute("UPDATE messages SET is_read = CASE WHEN direction = 'outbound' THEN TRUE ELSE FALSE END")


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_imap_uid"), table_name="messages")
    op.drop_column("messages", "is_read")
    op.drop_column("messages", "imap_uid")

    op.drop_constraint("fk_threads_contact_id", "threads", type_="foreignkey")
    op.drop_constraint("fk_threads_campaign_id", "threads", type_="foreignkey")
    op.drop_index(op.f("ix_threads_contact_email"), table_name="threads")
    op.drop_column("threads", "linkage_status")
    op.drop_column("threads", "contact_email")
    op.drop_column("threads", "contact_id")
    op.drop_column("threads", "campaign_id")

    op.drop_column("mailboxes", "inbox_last_seen_uid")
    op.drop_column("mailboxes", "inbox_last_error")
    op.drop_column("mailboxes", "inbox_last_success_at")
    op.drop_column("mailboxes", "inbox_last_synced_at")
    op.drop_column("mailboxes", "inbox_sync_status")
    op.drop_column("mailboxes", "inbox_sync_enabled")
