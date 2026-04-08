"""add b2b b2c shared fields

Revision ID: f58f5b5d6a10
Revises: c4f9f2d8d120
Create Date: 2026-04-09 00:25:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f58f5b5d6a10"
down_revision = "c4f9f2d8d120"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("industry", sa.String(), nullable=True))
    op.add_column("contacts", sa.Column("persona", sa.String(), nullable=True))
    op.add_column("contacts", sa.Column("contact_type", sa.String(), nullable=True))
    op.add_column("contacts", sa.Column("consent_status", sa.String(), nullable=False, server_default="unknown"))
    op.add_column("contacts", sa.Column("unsubscribe_status", sa.String(), nullable=False, server_default="subscribed"))
    op.add_column("contacts", sa.Column("engagement_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("contacts", sa.Column("contact_status", sa.String(), nullable=False, server_default="active"))

    op.execute(
        """
        ALTER TABLE contacts
        ALTER COLUMN tags TYPE JSONB
        USING CASE
            WHEN tags IS NULL OR btrim(tags) = '' THEN '[]'::jsonb
            ELSE to_jsonb(regexp_split_to_array(regexp_replace(tags, '\s*,\s*', ',', 'g'), ','))
        END
        """
    )

    op.add_column("campaigns", sa.Column("campaign_type", sa.String(), nullable=False, server_default="b2b"))
    op.add_column("campaigns", sa.Column("channel_type", sa.String(), nullable=False, server_default="email"))
    op.add_column("campaigns", sa.Column("goal_type", sa.String(), nullable=False, server_default="outreach"))
    op.add_column("campaigns", sa.Column("list_strategy", sa.String(), nullable=False, server_default="list_based"))
    op.add_column("campaigns", sa.Column("compliance_mode", sa.String(), nullable=False, server_default="standard"))
    op.add_column("campaigns", sa.Column("schedule_window", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("campaigns", sa.Column("send_window_timezone", sa.String(), nullable=True))

    op.alter_column("contacts", "consent_status", server_default=None)
    op.alter_column("contacts", "unsubscribe_status", server_default=None)
    op.alter_column("contacts", "engagement_score", server_default=None)
    op.alter_column("contacts", "contact_status", server_default=None)
    op.alter_column("campaigns", "campaign_type", server_default=None)
    op.alter_column("campaigns", "channel_type", server_default=None)
    op.alter_column("campaigns", "goal_type", server_default=None)
    op.alter_column("campaigns", "list_strategy", server_default=None)
    op.alter_column("campaigns", "compliance_mode", server_default=None)


def downgrade() -> None:
    op.drop_column("campaigns", "send_window_timezone")
    op.drop_column("campaigns", "schedule_window")
    op.drop_column("campaigns", "compliance_mode")
    op.drop_column("campaigns", "list_strategy")
    op.drop_column("campaigns", "goal_type")
    op.drop_column("campaigns", "channel_type")
    op.drop_column("campaigns", "campaign_type")

    op.execute(
        """
        ALTER TABLE contacts
        ALTER COLUMN tags TYPE VARCHAR
        USING CASE
            WHEN tags IS NULL THEN NULL
            ELSE array_to_string(ARRAY(SELECT jsonb_array_elements_text(tags)), ',')
        END
        """
    )

    op.drop_column("contacts", "contact_status")
    op.drop_column("contacts", "engagement_score")
    op.drop_column("contacts", "unsubscribe_status")
    op.drop_column("contacts", "consent_status")
    op.drop_column("contacts", "contact_type")
    op.drop_column("contacts", "persona")
    op.drop_column("contacts", "industry")
