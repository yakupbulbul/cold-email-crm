"""add warmup operational state

Revision ID: 4abf8d20c911
Revises: 9f6e61b2f2f4
Create Date: 2026-04-12 01:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "4abf8d20c911"
down_revision = "9f6e61b2f2f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mailboxes", sa.Column("warmup_status", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("warmup_last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("mailboxes", sa.Column("warmup_last_result", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("warmup_block_reason", sa.String(), nullable=True))

    op.add_column("warmup_pairs", sa.Column("state", sa.String(), nullable=True))
    op.add_column("warmup_pairs", sa.Column("last_sent_at", sa.DateTime(), nullable=True))
    op.add_column("warmup_pairs", sa.Column("next_scheduled_at", sa.DateTime(), nullable=True))
    op.add_column("warmup_pairs", sa.Column("last_result", sa.String(), nullable=True))
    op.add_column("warmup_pairs", sa.Column("last_error", sa.Text(), nullable=True))

    op.add_column("warmup_events", sa.Column("pair_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("warmup_events", sa.Column("recipient_mailbox_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("warmup_events", sa.Column("error_category", sa.String(), nullable=True))
    op.add_column("warmup_events", sa.Column("result_detail", sa.Text(), nullable=True))
    op.add_column("warmup_events", sa.Column("scheduled_for", sa.DateTime(), nullable=True))

    op.create_foreign_key("fk_warmup_events_pair_id", "warmup_events", "warmup_pairs", ["pair_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_warmup_events_recipient_mailbox_id", "warmup_events", "mailboxes", ["recipient_mailbox_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_warmup_pairs_sender_recipient", "warmup_pairs", ["sender_mailbox_id", "recipient_mailbox_id"])

    op.create_table(
        "warmup_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.execute("UPDATE warmup_pairs SET state = 'active' WHERE state IS NULL")
    op.alter_column("warmup_pairs", "state", nullable=False, server_default="active")


def downgrade() -> None:
    op.drop_table("warmup_settings")
    op.drop_constraint("uq_warmup_pairs_sender_recipient", "warmup_pairs", type_="unique")
    op.drop_constraint("fk_warmup_events_recipient_mailbox_id", "warmup_events", type_="foreignkey")
    op.drop_constraint("fk_warmup_events_pair_id", "warmup_events", type_="foreignkey")
    op.drop_column("warmup_events", "scheduled_for")
    op.drop_column("warmup_events", "result_detail")
    op.drop_column("warmup_events", "error_category")
    op.drop_column("warmup_events", "recipient_mailbox_id")
    op.drop_column("warmup_events", "pair_id")

    op.drop_column("warmup_pairs", "last_error")
    op.drop_column("warmup_pairs", "last_result")
    op.drop_column("warmup_pairs", "next_scheduled_at")
    op.drop_column("warmup_pairs", "last_sent_at")
    op.drop_column("warmup_pairs", "state")

    op.drop_column("mailboxes", "warmup_block_reason")
    op.drop_column("mailboxes", "warmup_last_result")
    op.drop_column("mailboxes", "warmup_last_checked_at")
    op.drop_column("mailboxes", "warmup_status")
