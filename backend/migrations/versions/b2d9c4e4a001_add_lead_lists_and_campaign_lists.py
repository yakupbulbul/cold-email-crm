"""add lead lists and campaign lists

Revision ID: b2d9c4e4a001
Revises: 9d43a8eb4f10
Create Date: 2026-04-08 23:15:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "b2d9c4e4a001"
down_revision = "9d43a8eb4f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("filter_definition", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lead_lists_name"), "lead_lists", ["name"], unique=True)

    op.create_table(
        "lead_list_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["list_id"], ["lead_lists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("list_id", "lead_id", name="uq_lead_list_members_list_id_lead_id"),
    )
    op.create_index(op.f("ix_lead_list_members_lead_id"), "lead_list_members", ["lead_id"], unique=False)
    op.create_index(op.f("ix_lead_list_members_list_id"), "lead_list_members", ["list_id"], unique=False)

    op.create_table(
        "campaign_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["list_id"], ["lead_lists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "list_id", name="uq_campaign_lists_campaign_id_list_id"),
    )
    op.create_index(op.f("ix_campaign_lists_campaign_id"), "campaign_lists", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_campaign_lists_list_id"), "campaign_lists", ["list_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_lists_list_id"), table_name="campaign_lists")
    op.drop_index(op.f("ix_campaign_lists_campaign_id"), table_name="campaign_lists")
    op.drop_table("campaign_lists")
    op.drop_index(op.f("ix_lead_list_members_list_id"), table_name="lead_list_members")
    op.drop_index(op.f("ix_lead_list_members_lead_id"), table_name="lead_list_members")
    op.drop_table("lead_list_members")
    op.drop_index(op.f("ix_lead_lists_name"), table_name="lead_lists")
    op.drop_table("lead_lists")
