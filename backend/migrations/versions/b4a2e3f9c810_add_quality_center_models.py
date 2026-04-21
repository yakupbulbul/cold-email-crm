"""add quality center models

Revision ID: b4a2e3f9c810
Revises: afe91c2d7b30
Create Date: 2026-04-22 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b4a2e3f9c810"
down_revision: Union[str, Sequence[str], None] = "afe91c2d7b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quality_check_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("triggered_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_check_runs_run_type"), "quality_check_runs", ["run_type"], unique=False)
    op.create_index(op.f("ix_quality_check_runs_status"), "quality_check_runs", ["status"], unique=False)

    op.create_table(
        "quality_check_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("href", sa.String(), nullable=True),
        sa.Column("metadata_blob", sa.JSON(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["quality_check_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_check_results_category"), "quality_check_results", ["category"], unique=False)
    op.create_index(op.f("ix_quality_check_results_entity_id"), "quality_check_results", ["entity_id"], unique=False)
    op.create_index(op.f("ix_quality_check_results_entity_type"), "quality_check_results", ["entity_type"], unique=False)
    op.create_index(op.f("ix_quality_check_results_run_id"), "quality_check_results", ["run_id"], unique=False)
    op.create_index(op.f("ix_quality_check_results_severity"), "quality_check_results", ["severity"], unique=False)
    op.create_index(op.f("ix_quality_check_results_status"), "quality_check_results", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quality_check_results_status"), table_name="quality_check_results")
    op.drop_index(op.f("ix_quality_check_results_severity"), table_name="quality_check_results")
    op.drop_index(op.f("ix_quality_check_results_run_id"), table_name="quality_check_results")
    op.drop_index(op.f("ix_quality_check_results_entity_type"), table_name="quality_check_results")
    op.drop_index(op.f("ix_quality_check_results_entity_id"), table_name="quality_check_results")
    op.drop_index(op.f("ix_quality_check_results_category"), table_name="quality_check_results")
    op.drop_table("quality_check_results")
    op.drop_index(op.f("ix_quality_check_runs_status"), table_name="quality_check_runs")
    op.drop_index(op.f("ix_quality_check_runs_run_type"), table_name="quality_check_runs")
    op.drop_table("quality_check_runs")

