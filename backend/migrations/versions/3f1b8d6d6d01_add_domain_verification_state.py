"""Add domain verification state

Revision ID: 3f1b8d6d6d01
Revises: 6c5b069ae5dc
Create Date: 2026-04-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3f1b8d6d6d01"
down_revision: Union[str, Sequence[str], None] = "6c5b069ae5dc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("domains", sa.Column("mailcow_status", sa.String(), nullable=True))
    op.add_column("domains", sa.Column("mailcow_detail", sa.String(), nullable=True))
    op.add_column("domains", sa.Column("dns_results", sa.JSON(), nullable=True))
    op.add_column("domains", sa.Column("missing_requirements", sa.JSON(), nullable=True))
    op.add_column("domains", sa.Column("verification_summary", sa.JSON(), nullable=True))
    op.add_column("domains", sa.Column("verification_error", sa.String(), nullable=True))
    op.add_column("domains", sa.Column("last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("domains", sa.Column("mailcow_last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("domains", sa.Column("dns_last_checked_at", sa.DateTime(), nullable=True))

    op.execute("UPDATE domains SET status = 'pending' WHERE status IS NULL OR status = 'active'")
    op.execute("UPDATE domains SET mailcow_status = 'pending' WHERE mailcow_status IS NULL")
    op.execute("UPDATE domains SET dns_results = '{}'::json WHERE dns_results IS NULL")
    op.execute("UPDATE domains SET missing_requirements = '[]'::json WHERE missing_requirements IS NULL")
    op.execute("UPDATE domains SET verification_summary = '{\"readiness\": {\"status\": \"pending\", \"missing_requirements\": []}}'::json WHERE verification_summary IS NULL")


def downgrade() -> None:
    op.drop_column("domains", "dns_last_checked_at")
    op.drop_column("domains", "mailcow_last_checked_at")
    op.drop_column("domains", "last_checked_at")
    op.drop_column("domains", "verification_error")
    op.drop_column("domains", "verification_summary")
    op.drop_column("domains", "missing_requirements")
    op.drop_column("domains", "dns_results")
    op.drop_column("domains", "mailcow_detail")
    op.drop_column("domains", "mailcow_status")
