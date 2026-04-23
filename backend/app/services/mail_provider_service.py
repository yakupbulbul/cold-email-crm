from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.imap.provider import (
    GoogleWorkspaceIMAPProvider,
    IMAPConnectionResult,
    IMAPFetchedMessage,
    IMAPProviderError,
    MailcowIMAPProvider,
)
from app.integrations.mailcow.client import MailcowClient
from app.integrations.smtp.provider import (
    GoogleWorkspaceSMTPProvider,
    MailcowSMTPProvider,
    SMTPDiagnosticResult,
)
from app.models.core import Mailbox
from app.services.google_oauth_service import GoogleOAuthError, GoogleWorkspaceOAuthService
from app.services.provider_settings_service import ProviderSettingsService


class ProviderUnavailableError(Exception):
    def __init__(self, message: str, *, category: str = "provider_unavailable", status_code: int = 409):
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code


@dataclass
class MailboxCapabilities:
    provider_type: str
    can_send: bool
    can_sync_inbox: bool
    can_warmup: bool
    uses_oauth: bool
    diagnostics: list[str]


class MailProviderAdapter(ABC):
    provider_type: str

    def __init__(self, db: Session):
        self.db = db

    @abstractmethod
    def send_email(self, mailbox: Mailbox, **kwargs) -> tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def diagnose_smtp(self, mailbox: Mailbox) -> SMTPDiagnosticResult:
        raise NotImplementedError

    @abstractmethod
    def diagnose_imap(self, mailbox: Mailbox) -> IMAPConnectionResult:
        raise NotImplementedError

    @abstractmethod
    def sync_inbox(self, mailbox: Mailbox) -> list[IMAPFetchedMessage]:
        raise NotImplementedError

    @abstractmethod
    def check_provider_health(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_mailbox_capabilities(self, mailbox: Mailbox) -> MailboxCapabilities:
        raise NotImplementedError

    def is_provider_available(self) -> tuple[bool, str | None]:
        return True, None


class MailcowProviderAdapter(MailProviderAdapter):
    provider_type = "mailcow"

    def __init__(self, db: Session):
        super().__init__(db)
        self.smtp = MailcowSMTPProvider()
        self.imap = MailcowIMAPProvider()
        self.client = MailcowClient()

    def send_email(self, mailbox: Mailbox, **kwargs) -> tuple[bool, str]:
        return self.smtp.send_email(
            host=mailbox.smtp_host,
            port=mailbox.smtp_port,
            username=mailbox.smtp_username,
            password=mailbox.smtp_password_encrypted,
            security_mode=(mailbox.smtp_security_mode or "").strip().lower() or ("ssl" if mailbox.smtp_port == 465 else "starttls"),
            **kwargs,
        )

    def diagnose_smtp(self, mailbox: Mailbox) -> SMTPDiagnosticResult:
        return self.smtp.diagnose_connection(
            host=mailbox.smtp_host,
            port=mailbox.smtp_port,
            username=mailbox.smtp_username,
            password=mailbox.smtp_password_encrypted,
            security_mode=(mailbox.smtp_security_mode or "").strip().lower() or ("ssl" if mailbox.smtp_port == 465 else "starttls"),
        )

    def diagnose_imap(self, mailbox: Mailbox) -> IMAPConnectionResult:
        return self.imap.diagnose_connection(
            mailbox.imap_host,
            mailbox.imap_port,
            mailbox.imap_username,
            mailbox.imap_password_encrypted,
        )

    def sync_inbox(self, mailbox: Mailbox) -> list[IMAPFetchedMessage]:
        return self.imap.fetch_messages(
            mailbox.imap_host,
            mailbox.imap_port,
            mailbox.imap_username,
            mailbox.imap_password_encrypted,
            since_uid=mailbox.inbox_last_seen_uid,
        )

    def check_provider_health(self) -> dict:
        result = self.client.check_health()
        return {
            "status": result.status,
            "configured": result.configured,
            "detail": result.detail,
            "reason": result.reason,
        }

    def get_mailbox_capabilities(self, mailbox: Mailbox) -> MailboxCapabilities:
        return MailboxCapabilities(
            provider_type=self.provider_type,
            can_send=True,
            can_sync_inbox=True,
            can_warmup=True,
            uses_oauth=False,
            diagnostics=["smtp", "imap", "mailcow_api"],
        )

    def is_provider_available(self) -> tuple[bool, str | None]:
        return True, None


class GoogleWorkspaceProviderAdapter(MailProviderAdapter):
    provider_type = "google_workspace"

    def __init__(self, db: Session):
        super().__init__(db)
        self.smtp = GoogleWorkspaceSMTPProvider()
        self.imap = GoogleWorkspaceIMAPProvider()
        self.oauth = GoogleWorkspaceOAuthService(db)

    def _access_token(self, mailbox: Mailbox) -> str:
        return self.oauth.get_valid_access_token(mailbox)

    def send_email(self, mailbox: Mailbox, **kwargs) -> tuple[bool, str]:
        access_token = self._access_token(mailbox)
        return self.smtp.send_email(
            host=mailbox.smtp_host,
            port=mailbox.smtp_port,
            username=mailbox.smtp_username,
            access_token=access_token,
            security_mode=(mailbox.smtp_security_mode or "").strip().lower() or ("ssl" if mailbox.smtp_port == 465 else "starttls"),
            **kwargs,
        )

    def diagnose_smtp(self, mailbox: Mailbox) -> SMTPDiagnosticResult:
        access_token = self._access_token(mailbox)
        return self.smtp.diagnose_connection(
            host=mailbox.smtp_host,
            port=mailbox.smtp_port,
            username=mailbox.smtp_username,
            access_token=access_token,
            security_mode=(mailbox.smtp_security_mode or "").strip().lower() or ("ssl" if mailbox.smtp_port == 465 else "starttls"),
        )

    def diagnose_imap(self, mailbox: Mailbox) -> IMAPConnectionResult:
        access_token = self._access_token(mailbox)
        return self.imap.diagnose_connection(
            mailbox.imap_host,
            mailbox.imap_port,
            mailbox.imap_username,
            access_token,
        )

    def sync_inbox(self, mailbox: Mailbox) -> list[IMAPFetchedMessage]:
        access_token = self._access_token(mailbox)
        return self.imap.fetch_messages(
            mailbox.imap_host,
            mailbox.imap_port,
            mailbox.imap_username,
            access_token,
            since_uid=mailbox.inbox_last_seen_uid,
        )

    def check_provider_health(self) -> dict:
        if not self.oauth.is_configured():
            return {
                "status": "misconfigured",
                "configured": False,
                "detail": "Google Workspace OAuth credentials are not configured on the backend.",
                "reason": "provider_misconfigured",
            }
        return {
            "status": "healthy",
            "configured": True,
            "detail": "Google Workspace OAuth credentials are configured.",
            "reason": None,
        }

    def get_mailbox_capabilities(self, mailbox: Mailbox) -> MailboxCapabilities:
        status = mailbox.oauth_connection_status or "not_connected"
        connected = status == "connected"
        return MailboxCapabilities(
            provider_type=self.provider_type,
            can_send=connected,
            can_sync_inbox=connected,
            can_warmup=connected,
            uses_oauth=True,
            diagnostics=["smtp", "imap", "oauth"],
        )

    def is_provider_available(self) -> tuple[bool, str | None]:
        if not self.oauth.is_configured():
            return False, "Google Workspace OAuth is not configured on the backend."
        return True, None


class MailProviderRegistry:
    def __init__(self, db: Session):
        self.db = db
        self.settings_service = ProviderSettingsService(db)

    def get_provider_settings(self):
        return self.settings_service.get_or_create()

    def get_enabled_provider_map(self) -> dict[str, bool]:
        row = self.get_provider_settings()
        return {
            "mailcow": row.mailcow_enabled,
            "google_workspace": row.google_workspace_enabled,
        }

    def get_provider(self, provider_type: str) -> MailProviderAdapter:
        normalized = (provider_type or "mailcow").strip().lower()
        if normalized == "mailcow":
            return MailcowProviderAdapter(self.db)
        if normalized == "google_workspace":
            return GoogleWorkspaceProviderAdapter(self.db)
        raise ProviderUnavailableError(f"Unsupported mailbox provider '{provider_type}'.", category="unsupported_provider", status_code=400)

    def ensure_provider_allowed(self, provider_type: str, *, mailbox: Mailbox | None = None) -> None:
        settings_row = self.get_provider_settings()
        enabled_map = self.get_enabled_provider_map()
        normalized = (provider_type or "mailcow").strip().lower()
        if enabled_map.get(normalized, False):
            return
        if mailbox is not None and settings_row.allow_existing_disabled_provider_mailboxes:
            return
        raise ProviderUnavailableError(
            f"The {normalized.replace('_', ' ')} provider is disabled in settings.",
            category="provider_disabled",
            status_code=409,
        )

    def resolve_mailbox_provider(self, mailbox: Mailbox) -> MailProviderAdapter:
        self.ensure_provider_allowed(mailbox.provider_type or "mailcow", mailbox=mailbox)
        provider = self.get_provider(mailbox.provider_type or "mailcow")
        available, reason = provider.is_provider_available()
        if not available:
            raise ProviderUnavailableError(reason or "The mailbox provider is not available.", category="provider_unavailable", status_code=424)
        return provider

    def provider_health_payload(self) -> dict[str, dict]:
        payload: dict[str, dict] = {}
        enabled_map = self.get_enabled_provider_map()
        for provider_type in ["mailcow", "google_workspace"]:
            adapter = self.get_provider(provider_type)
            health = adapter.check_provider_health()
            payload[provider_type] = {
                "enabled": enabled_map.get(provider_type, False),
                "configured": health.get("configured", False),
                "status": health.get("status", "unknown"),
                "detail": health.get("detail"),
                "reason": health.get("reason"),
                "checked_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }
        return payload
