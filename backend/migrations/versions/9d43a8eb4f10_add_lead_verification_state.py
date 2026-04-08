"""Add lead verification state

Revision ID: 9d43a8eb4f10
Revises: 3f1b8d6d6d01
Create Date: 2026-04-08 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9d43a8eb4f10"
down_revision: Union[str, Sequence[str], None] = "3f1b8d6d6d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("verification_integrity", sa.String(), nullable=True))
    op.add_column("contacts", sa.Column("verification_reasons", sa.JSON(), nullable=True))
    op.alter_column("contacts", "verification_score", existing_type=sa.Integer(), nullable=True)
    op.execute("UPDATE contacts SET email_status = 'unverified' WHERE email_status IS NULL OR email_status IN ('new', '')")
    op.execute("UPDATE contacts SET verification_score = NULL WHERE last_verified_at IS NULL")

    op.add_column("email_verification_logs", sa.Column("duplicate", sa.Boolean(), nullable=True))
    op.add_column("email_verification_logs", sa.Column("verification_integrity", sa.String(), nullable=True))
    op.add_column("email_verification_logs", sa.Column("verification_reasons", sa.JSON(), nullable=True))
    op.execute("UPDATE email_verification_logs SET duplicate = FALSE WHERE duplicate IS NULL")
    op.execute("UPDATE email_verification_logs SET verification_reasons = '[]'::json WHERE verification_reasons IS NULL")


def downgrade() -> None:
    op.drop_column("email_verification_logs", "verification_reasons")
    op.drop_column("email_verification_logs", "verification_integrity")
    op.drop_column("email_verification_logs", "duplicate")

    op.execute("UPDATE contacts SET verification_score = 0 WHERE verification_score IS NULL")
    op.alter_column("contacts", "verification_score", existing_type=sa.Integer(), nullable=False)
    op.drop_column("contacts", "verification_reasons")
    op.drop_column("contacts", "verification_integrity")
