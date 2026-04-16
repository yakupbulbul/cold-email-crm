from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.core import MailProviderSetting


class ProviderSettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self) -> MailProviderSetting:
        row = self.db.query(MailProviderSetting).order_by(MailProviderSetting.created_at.asc()).first()
        if row is not None:
            return row
        row = MailProviderSetting(
            mailcow_enabled=True,
            google_workspace_enabled=False,
            default_provider="mailcow",
            allow_existing_disabled_provider_mailboxes=False,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def update(
        self,
        *,
        mailcow_enabled: bool | None = None,
        google_workspace_enabled: bool | None = None,
        default_provider: str | None = None,
        allow_existing_disabled_provider_mailboxes: bool | None = None,
    ) -> MailProviderSetting:
        row = self.get_or_create()
        if mailcow_enabled is not None:
            row.mailcow_enabled = mailcow_enabled
        if google_workspace_enabled is not None:
            row.google_workspace_enabled = google_workspace_enabled
        if default_provider is not None:
            row.default_provider = default_provider
        if allow_existing_disabled_provider_mailboxes is not None:
            row.allow_existing_disabled_provider_mailboxes = allow_existing_disabled_provider_mailboxes
        row.updated_at = datetime.utcnow()
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
