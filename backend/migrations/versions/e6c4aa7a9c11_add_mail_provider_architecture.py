"""add mail provider architecture

Revision ID: e6c4aa7a9c11
Revises: 18c4b6ee2f10
Create Date: 2026-04-15 11:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


revision = "e6c4aa7a9c11"
down_revision = "18c4b6ee2f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mailboxes", sa.Column("provider_type", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("provider_status", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("provider_mailbox_id", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("provider_domain_id", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("provider_config_status", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("last_provider_check_at", sa.DateTime(), nullable=True))
    op.add_column("mailboxes", sa.Column("last_provider_check_status", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("last_provider_check_message", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("imap_security_mode", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("oauth_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("mailboxes", sa.Column("oauth_provider", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("oauth_connection_status", sa.String(), nullable=True))
    op.add_column("mailboxes", sa.Column("oauth_last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("mailboxes", sa.Column("oauth_last_error", sa.String(), nullable=True))

    op.execute("UPDATE mailboxes SET provider_type = 'mailcow' WHERE provider_type IS NULL")
    op.execute("UPDATE mailboxes SET provider_status = 'active' WHERE provider_status IS NULL")
    op.execute("UPDATE mailboxes SET provider_config_status = 'configured' WHERE provider_config_status IS NULL")
    op.execute(
        """
        UPDATE mailboxes
        SET imap_security_mode = CASE
            WHEN imap_port = 143 THEN 'plain'
            ELSE 'ssl'
        END
        WHERE imap_security_mode IS NULL
        """
    )
    op.execute(
        """
        UPDATE mailboxes
        SET oauth_enabled = false,
            oauth_provider = NULL,
            oauth_connection_status = NULL
        WHERE oauth_enabled IS NULL
        """
    )

    op.alter_column("mailboxes", "provider_type", nullable=False, server_default="mailcow")
    op.alter_column("mailboxes", "provider_status", nullable=False, server_default="active")
    op.alter_column("mailboxes", "provider_config_status", nullable=False, server_default="configured")
    op.alter_column("mailboxes", "imap_security_mode", nullable=False, server_default="ssl")
    op.alter_column("mailboxes", "oauth_enabled", server_default=None)

    op.create_index("ix_mailboxes_provider_type", "mailboxes", ["provider_type"], unique=False)

    op.create_table(
        "mail_provider_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mailcow_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("google_workspace_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("default_provider", sa.String(), nullable=False, server_default="mailcow"),
        sa.Column("allow_existing_disabled_provider_mailboxes", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mailcow_last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("mailcow_last_check_status", sa.String(), nullable=True),
        sa.Column("mailcow_last_check_message", sa.String(), nullable=True),
        sa.Column("google_workspace_last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("google_workspace_last_check_status", sa.String(), nullable=True),
        sa.Column("google_workspace_last_check_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "mailbox_oauth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mailbox_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.String(), nullable=False, server_default="google_workspace"),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column("token_type", sa.String(), nullable=True),
        sa.Column("external_account_email", sa.String(), nullable=True),
        sa.Column("connection_status", sa.String(), nullable=False, server_default="not_connected"),
        sa.Column("last_refreshed_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["mailbox_id"], ["mailboxes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mailbox_id"),
    )

    op.execute(
        """
        INSERT INTO mail_provider_settings (
            id,
            mailcow_enabled,
            google_workspace_enabled,
            default_provider,
            allow_existing_disabled_provider_mailboxes,
            created_at,
            updated_at
        )
        SELECT '%s', true, false, 'mailcow', false, NOW(), NOW()
        WHERE NOT EXISTS (SELECT 1 FROM mail_provider_settings)
        """
        % str(uuid.uuid4())
    )


def downgrade() -> None:
    op.drop_table("mailbox_oauth_tokens")
    op.drop_table("mail_provider_settings")
    op.drop_index("ix_mailboxes_provider_type", table_name="mailboxes")
    op.drop_column("mailboxes", "oauth_last_error")
    op.drop_column("mailboxes", "oauth_last_checked_at")
    op.drop_column("mailboxes", "oauth_connection_status")
    op.drop_column("mailboxes", "oauth_provider")
    op.drop_column("mailboxes", "oauth_enabled")
    op.drop_column("mailboxes", "imap_security_mode")
    op.drop_column("mailboxes", "last_provider_check_message")
    op.drop_column("mailboxes", "last_provider_check_status")
    op.drop_column("mailboxes", "last_provider_check_at")
    op.drop_column("mailboxes", "provider_config_status")
    op.drop_column("mailboxes", "provider_domain_id")
    op.drop_column("mailboxes", "provider_mailbox_id")
    op.drop_column("mailboxes", "provider_status")
    op.drop_column("mailboxes", "provider_type")
