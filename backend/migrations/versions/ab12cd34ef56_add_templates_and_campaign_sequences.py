"""add templates and campaign sequences

Revision ID: ab12cd34ef56
Revises: e6c4aa7a9c11
Create Date: 2026-04-20 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "ab12cd34ef56"
down_revision: Union[str, Sequence[str], None] = "e6c4aa7a9c11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "campaign_sequence_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("delay_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("stop_on_reply", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "step_number", name="uq_campaign_sequence_steps_campaign_step"),
    )
    op.create_index(op.f("ix_campaign_sequence_steps_campaign_id"), "campaign_sequence_steps", ["campaign_id"], unique=False)
    op.add_column("campaign_leads", sa.Column("sequence_step_index", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("campaign_leads", "sequence_step_index")
    op.drop_index(op.f("ix_campaign_sequence_steps_campaign_id"), table_name="campaign_sequence_steps")
    op.drop_table("campaign_sequence_steps")
    op.drop_table("email_templates")
