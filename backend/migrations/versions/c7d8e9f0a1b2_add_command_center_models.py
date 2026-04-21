"""add command center models

Revision ID: c7d8e9f0a1b2
Revises: ab12cd34ef56
Create Date: 2026-04-21 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "ab12cd34ef56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operator_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("related_entity_type", sa.String(), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_blob", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operator_tasks_category"), "operator_tasks", ["category"], unique=False)
    op.create_index(op.f("ix_operator_tasks_due_at"), "operator_tasks", ["due_at"], unique=False)
    op.create_index(op.f("ix_operator_tasks_priority"), "operator_tasks", ["priority"], unique=False)
    op.create_index(op.f("ix_operator_tasks_related_entity_id"), "operator_tasks", ["related_entity_id"], unique=False)
    op.create_index(op.f("ix_operator_tasks_related_entity_type"), "operator_tasks", ["related_entity_type"], unique=False)
    op.create_index(op.f("ix_operator_tasks_status"), "operator_tasks", ["status"], unique=False)

    op.create_table(
        "operator_action_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_entity_type", sa.String(), nullable=True),
        sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_blob", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operator_action_logs_action_type"), "operator_action_logs", ["action_type"], unique=False)
    op.create_index(op.f("ix_operator_action_logs_created_at"), "operator_action_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_operator_action_logs_related_entity_id"), "operator_action_logs", ["related_entity_id"], unique=False)
    op.create_index(op.f("ix_operator_action_logs_related_entity_type"), "operator_action_logs", ["related_entity_type"], unique=False)
    op.create_index(op.f("ix_operator_action_logs_result"), "operator_action_logs", ["result"], unique=False)
    op.create_index(op.f("ix_operator_action_logs_source"), "operator_action_logs", ["source"], unique=False)

    op.create_table(
        "daily_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_date", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_date"),
    )
    op.create_index(op.f("ix_daily_notes_note_date"), "daily_notes", ["note_date"], unique=False)

    op.create_table(
        "runbooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runbooks_category"), "runbooks", ["category"], unique=False)
    op.create_index(op.f("ix_runbooks_is_active"), "runbooks", ["is_active"], unique=False)

    op.create_table(
        "runbook_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runbook_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["runbook_id"], ["runbooks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_runbook_steps_runbook_id"), "runbook_steps", ["runbook_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_runbook_steps_runbook_id"), table_name="runbook_steps")
    op.drop_table("runbook_steps")
    op.drop_index(op.f("ix_runbooks_is_active"), table_name="runbooks")
    op.drop_index(op.f("ix_runbooks_category"), table_name="runbooks")
    op.drop_table("runbooks")
    op.drop_index(op.f("ix_daily_notes_note_date"), table_name="daily_notes")
    op.drop_table("daily_notes")
    op.drop_index(op.f("ix_operator_action_logs_source"), table_name="operator_action_logs")
    op.drop_index(op.f("ix_operator_action_logs_result"), table_name="operator_action_logs")
    op.drop_index(op.f("ix_operator_action_logs_related_entity_type"), table_name="operator_action_logs")
    op.drop_index(op.f("ix_operator_action_logs_related_entity_id"), table_name="operator_action_logs")
    op.drop_index(op.f("ix_operator_action_logs_created_at"), table_name="operator_action_logs")
    op.drop_index(op.f("ix_operator_action_logs_action_type"), table_name="operator_action_logs")
    op.drop_table("operator_action_logs")
    op.drop_index(op.f("ix_operator_tasks_status"), table_name="operator_tasks")
    op.drop_index(op.f("ix_operator_tasks_related_entity_type"), table_name="operator_tasks")
    op.drop_index(op.f("ix_operator_tasks_related_entity_id"), table_name="operator_tasks")
    op.drop_index(op.f("ix_operator_tasks_priority"), table_name="operator_tasks")
    op.drop_index(op.f("ix_operator_tasks_due_at"), table_name="operator_tasks")
    op.drop_index(op.f("ix_operator_tasks_category"), table_name="operator_tasks")
    op.drop_table("operator_tasks")
