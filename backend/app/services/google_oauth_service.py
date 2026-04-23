from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import decrypt_value, encrypt_value
from app.models.core import Mailbox, MailboxOAuthToken


class GoogleOAuthError(Exception):
    def __init__(self, message: str, *, category: str = "oauth_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.category = category
        self.status_code = status_code


class GoogleWorkspaceOAuthService:
    provider_name = "google_workspace"

    def __init__(self, db: Session):
        self.db = db

    def is_configured(self) -> bool:
        return bool(
            settings.GOOGLE_WORKSPACE_CLIENT_ID
            and settings.GOOGLE_WORKSPACE_CLIENT_SECRET
            and settings.GOOGLE_WORKSPACE_REDIRECT_URI
        )

    def build_authorization_url(self, mailbox: Mailbox) -> str:
        if not self.is_configured():
            raise GoogleOAuthError(
                "Google Workspace OAuth is not configured on the backend.",
                category="provider_misconfigured",
                status_code=424,
            )
        state = jwt.encode(
            {
                "mailbox_id": str(mailbox.id),
                "provider": self.provider_name,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            },
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        query = urlencode(
            {
                "client_id": settings.GOOGLE_WORKSPACE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_WORKSPACE_REDIRECT_URI,
                "response_type": "code",
                "scope": " ".join(settings.GOOGLE_WORKSPACE_SCOPES),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
                "login_hint": mailbox.email,
            }
        )
        return f"{settings.GOOGLE_WORKSPACE_AUTH_URI}?{query}"

    def decode_state(self, state: str) -> dict:
        try:
            return jwt.decode(state, settings.SECRET_KEY, algorithms=["HS256"])
        except Exception as exc:
            raise GoogleOAuthError("OAuth state is invalid or expired.", category="invalid_state", status_code=400) from exc

    def exchange_code(self, *, code: str, state: str) -> MailboxOAuthToken:
        if not self.is_configured():
            raise GoogleOAuthError(
                "Google Workspace OAuth is not configured on the backend.",
                category="provider_misconfigured",
                status_code=424,
            )
        payload = self.decode_state(state)

        mailbox = self.db.query(Mailbox).filter(Mailbox.id == payload.get("mailbox_id")).first()
        if mailbox is None:
            raise GoogleOAuthError("Mailbox not found for OAuth callback.", category="mailbox_not_found", status_code=404)

        token_payload = self._token_request(
            {
                "code": code,
                "client_id": settings.GOOGLE_WORKSPACE_CLIENT_ID,
                "client_secret": settings.GOOGLE_WORKSPACE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_WORKSPACE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )
        return self._persist_token(mailbox, token_payload)

    def disconnect(self, mailbox: Mailbox) -> Mailbox:
        token = mailbox.oauth_token or self._ensure_token_row(mailbox)
        token.access_token_encrypted = None
        token.refresh_token_encrypted = None
        token.token_expiry = None
        token.scopes = None
        token.token_type = None
        token.connection_status = "not_connected"
        token.last_error = None
        token.external_account_email = None
        mailbox.oauth_connection_status = "not_connected"
        mailbox.oauth_last_checked_at = datetime.now(timezone.utc)
        mailbox.oauth_last_error = None
        self.db.add(token)
        self.db.add(mailbox)
        self.db.commit()
        self.db.refresh(mailbox)
        return mailbox

    def safe_status(self, mailbox: Mailbox) -> dict:
        token = mailbox.oauth_token
        connected = bool(token and token.refresh_token_encrypted)
        status = mailbox.oauth_connection_status or (token.connection_status if token else None) or ("connected" if connected else "not_connected")
        return {
            "oauth_enabled": mailbox.oauth_enabled,
            "oauth_provider": mailbox.oauth_provider,
            "oauth_connection_status": status,
            "oauth_last_checked_at": mailbox.oauth_last_checked_at.isoformat() if mailbox.oauth_last_checked_at else None,
            "oauth_last_error": mailbox.oauth_last_error,
            "oauth_last_refreshed_at": token.last_refreshed_at.isoformat() if token and token.last_refreshed_at else None,
            "oauth_token_expires_at": token.token_expiry.isoformat() if token and token.token_expiry else None,
            "external_account_email": token.external_account_email if token else None,
            "scopes": token.scopes if token and token.scopes else [],
        }

    def get_valid_access_token(self, mailbox: Mailbox) -> str:
        token = mailbox.oauth_token
        if token is None or not token.refresh_token_encrypted:
            raise GoogleOAuthError(
                "Google Workspace mailbox is not connected with OAuth.",
                category="needs_reauth",
                status_code=409,
            )
        if token.token_expiry and token.token_expiry > datetime.now(timezone.utc) + timedelta(minutes=2):
            access_token = decrypt_value(token.access_token_encrypted)
            if access_token:
                return access_token
        return self.refresh_access_token(mailbox)

    def refresh_access_token(self, mailbox: Mailbox) -> str:
        token = mailbox.oauth_token
        if token is None or not token.refresh_token_encrypted:
            raise GoogleOAuthError(
                "Google Workspace mailbox is not connected with OAuth.",
                category="needs_reauth",
                status_code=409,
            )
        if not self.is_configured():
            raise GoogleOAuthError(
                "Google Workspace OAuth is not configured on the backend.",
                category="provider_misconfigured",
                status_code=424,
            )
        token_payload = self._token_request(
            {
                "refresh_token": decrypt_value(token.refresh_token_encrypted),
                "client_id": settings.GOOGLE_WORKSPACE_CLIENT_ID,
                "client_secret": settings.GOOGLE_WORKSPACE_CLIENT_SECRET,
                "grant_type": "refresh_token",
            }
        )
        updated = self._persist_token(mailbox, token_payload, preserve_refresh_token=True)
        access_token = decrypt_value(updated.access_token_encrypted)
        if not access_token:
            raise GoogleOAuthError("Google Workspace refresh did not return an access token.", category="oauth_refresh_failed", status_code=502)
        return access_token

    def _token_request(self, payload: dict) -> dict:
        try:
            response = httpx.post(
                settings.GOOGLE_WORKSPACE_TOKEN_URI,
                data=payload,
                timeout=10,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:300] if exc.response is not None else "unknown_error"
            raise GoogleOAuthError(
                f"Google OAuth token exchange failed: {detail}",
                category="oauth_exchange_failed",
                status_code=502,
            ) from exc
        except httpx.HTTPError as exc:
            raise GoogleOAuthError(
                f"Google OAuth request failed: {exc}",
                category="oauth_unreachable",
                status_code=502,
            ) from exc

    def _ensure_token_row(self, mailbox: Mailbox) -> MailboxOAuthToken:
        token = mailbox.oauth_token
        if token is not None:
            return token
        token = MailboxOAuthToken(mailbox_id=mailbox.id, provider_type=self.provider_name)
        self.db.add(token)
        self.db.flush()
        return token

    def _persist_token(self, mailbox: Mailbox, payload: dict, *, preserve_refresh_token: bool = False) -> MailboxOAuthToken:
        token = self._ensure_token_row(mailbox)
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        expires_in = int(payload.get("expires_in") or 3600)
        token.access_token_encrypted = encrypt_value(access_token) if access_token else token.access_token_encrypted
        if refresh_token or not preserve_refresh_token:
            token.refresh_token_encrypted = encrypt_value(refresh_token) if refresh_token else token.refresh_token_encrypted
        token.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        token.scopes = (payload.get("scope") or "").split() if isinstance(payload.get("scope"), str) else payload.get("scope")
        token.token_type = payload.get("token_type")
        token.connection_status = "connected"
        token.last_refreshed_at = datetime.now(timezone.utc)
        token.last_error = None

        mailbox.oauth_enabled = True
        mailbox.oauth_provider = self.provider_name
        mailbox.oauth_connection_status = "connected"
        mailbox.oauth_last_checked_at = datetime.now(timezone.utc)
        mailbox.oauth_last_error = None

        if "id_token" in payload:
            try:
                decoded = jwt.get_unverified_claims(payload["id_token"])
                token.external_account_email = decoded.get("email")
            except Exception:
                token.external_account_email = mailbox.email
        elif token.external_account_email is None:
            token.external_account_email = mailbox.email

        self.db.add(token)
        self.db.add(mailbox)
        self.db.commit()
        self.db.refresh(token)
        self.db.refresh(mailbox)
        return token
