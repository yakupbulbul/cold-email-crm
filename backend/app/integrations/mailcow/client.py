from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import settings


class MailcowError(Exception):
    pass


@dataclass
class MailcowHealth:
    status: str
    detail: str
    http_status: int | None = None
    reason: str | None = None
    configured: bool = False
    reachable: bool = False
    header_attached: bool = False
    base_url: str | None = None
    request_path: str | None = None


@dataclass
class MailcowDomainLookup:
    status: str
    detail: str
    exists: bool
    http_status: int | None = None
    reason: str | None = None


@dataclass
class MailcowMailboxProvisionResult:
    status: str
    detail: str
    created: bool
    http_status: int | None = None
    reason: str | None = None


class MailcowClient:
    def __init__(self) -> None:
        self.api_url = settings.MAILCOW_API_URL.rstrip("/") if settings.MAILCOW_API_URL else None
        self.api_key = settings.MAILCOW_API_KEY
        self.timeout = settings.MAILCOW_API_TIMEOUT_SECONDS
        self.verify_ssl = settings.MAILCOW_VERIFY_SSL

    @property
    def configured(self) -> bool:
        return bool(self.api_url and self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise MailcowError("Mailcow API key is not configured")
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> httpx.Response:
        if not self.api_url:
            raise MailcowError("Mailcow API URL is not configured")
        with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
            response = client.request(
                method=method,
                url=f"{self.api_url}/{path.lstrip('/')}",
                headers=self._headers(),
                json=payload,
            )
        return response

    def _safe_base_url(self) -> str | None:
        if not self.api_url:
            return None
        parts = urlsplit(self.api_url)
        return f"{parts.scheme}://{parts.netloc}{parts.path}"

    def check_health(self) -> MailcowHealth:
        request_path = "/get/status/containers"
        if not self.configured:
            return MailcowHealth(
                status="unknown",
                detail="Mailcow API credentials are not configured for this environment.",
                reason="unconfigured",
                configured=False,
                reachable=False,
                header_attached=False,
                base_url=self._safe_base_url(),
                request_path=request_path,
            )

        try:
            response = self._request("GET", request_path)
        except httpx.HTTPError as exc:
            return MailcowHealth(
                status="failed",
                detail=f"Mailcow API unreachable: {exc}",
                reason="unreachable",
                configured=True,
                reachable=False,
                header_attached=True,
                base_url=self._safe_base_url(),
                request_path=request_path,
            )
        except MailcowError as exc:
            return MailcowHealth(
                status="failed",
                detail=str(exc),
                reason="misconfigured",
                configured=bool(self.api_url),
                reachable=False,
                header_attached=bool(self.api_key),
                base_url=self._safe_base_url(),
                request_path=request_path,
            )

        if response.status_code == 200:
            return MailcowHealth(
                status="healthy",
                detail="Mailcow API responded successfully.",
                http_status=200,
                reason="healthy",
                configured=True,
                reachable=True,
                header_attached=True,
                base_url=self._safe_base_url(),
                request_path=request_path,
            )
        if response.status_code in {401, 403}:
            return MailcowHealth(
                status="failed",
                detail="Mailcow API rejected the configured credentials.",
                http_status=response.status_code,
                reason="unauthorized",
                configured=True,
                reachable=True,
                header_attached=True,
                base_url=self._safe_base_url(),
                request_path=request_path,
            )
        return MailcowHealth(
            status="degraded",
            detail=f"Mailcow API returned an unexpected status code ({response.status_code}).",
            http_status=response.status_code,
            reason="unexpected_response",
            configured=True,
            reachable=True,
            header_attached=True,
            base_url=self._safe_base_url(),
            request_path=request_path,
        )

    def domain_exists(self, domain_name: str) -> bool | None:
        result = self.lookup_domain(domain_name)
        if result.status == "verified":
            return True
        if result.status == "not_found":
            return False
        return None

    def lookup_domain(self, domain_name: str) -> MailcowDomainLookup:
        if not self.configured:
            return MailcowDomainLookup(
                status="unconfigured",
                detail="Mailcow API credentials are not configured for this environment.",
                exists=False,
                reason="unconfigured",
            )
        try:
            response = self._request("GET", f"/get/domain/{domain_name}")
        except httpx.HTTPError as exc:
            return MailcowDomainLookup(
                status="unreachable",
                detail=f"Mailcow API unreachable: {exc}",
                exists=False,
                reason="unreachable",
            )
        except MailcowError as exc:
            return MailcowDomainLookup(
                status="error",
                detail=str(exc),
                exists=False,
                reason="misconfigured",
            )

        if response.status_code in {401, 403}:
            return MailcowDomainLookup(
                status="unauthorized",
                detail="Mailcow API rejected the configured credentials.",
                exists=False,
                http_status=response.status_code,
                reason="unauthorized",
            )
        if response.status_code == 200:
            payload: Any = response.json()
            exists = bool(payload)
            return MailcowDomainLookup(
                status="verified" if exists else "not_found",
                detail="Domain found in remote Mailcow." if exists else "Domain not found in remote Mailcow.",
                exists=exists,
                http_status=200,
                reason="healthy" if exists else "not_found",
            )
        if response.status_code == 404:
            return MailcowDomainLookup(
                status="not_found",
                detail="Domain not found in remote Mailcow.",
                exists=False,
                http_status=404,
                reason="not_found",
            )
        return MailcowDomainLookup(
            status="unexpected_response",
            detail=f"Mailcow API returned an unexpected status code ({response.status_code}).",
            exists=False,
            http_status=response.status_code,
            reason="unexpected_response",
        )

    def create_mailbox(
        self,
        *,
        email: str,
        display_name: str,
        password: str,
    ) -> MailcowMailboxProvisionResult:
        if not self.configured:
            return MailcowMailboxProvisionResult(
                status="misconfigured",
                detail="Mailcow API credentials are not configured for this environment.",
                created=False,
                reason="misconfigured",
            )

        local_part, separator, domain_name = email.partition("@")
        if not separator or not local_part or not domain_name:
            return MailcowMailboxProvisionResult(
                status="invalid",
                detail="Mailbox email must contain a valid local part and domain.",
                created=False,
                reason="invalid_email",
            )

        payload = {
            "active": True,
            "domain": domain_name,
            "local_part": local_part,
            "name": display_name,
            "authsource": "mailcow",
            "password": password,
            "password2": password,
        }

        try:
            response = self._request("POST", "/add/mailbox", payload)
        except httpx.HTTPError as exc:
            return MailcowMailboxProvisionResult(
                status="unreachable",
                detail=f"Mailcow API unreachable: {exc}",
                created=False,
                reason="unreachable",
            )
        except MailcowError as exc:
            return MailcowMailboxProvisionResult(
                status="misconfigured",
                detail=str(exc),
                created=False,
                reason="misconfigured",
            )

        if response.status_code in {401, 403}:
            return MailcowMailboxProvisionResult(
                status="unauthorized",
                detail="Mailcow API rejected the configured credentials.",
                created=False,
                http_status=response.status_code,
                reason="unauthorized",
            )

        if response.status_code != 200:
            return MailcowMailboxProvisionResult(
                status="unexpected_response",
                detail=f"Mailcow API returned an unexpected status code ({response.status_code}).",
                created=False,
                http_status=response.status_code,
                reason="unexpected_response",
            )

        entries = self._normalize_result_entries(response.json())
        for entry in entries:
            entry_type = str(entry.get("type", "")).lower()
            message_text = self._entry_text(entry)
            if entry_type == "success":
                return MailcowMailboxProvisionResult(
                    status="created",
                    detail="Mailbox created in remote Mailcow.",
                    created=True,
                    http_status=200,
                    reason="created",
                )
            if "already exists" in message_text or "exists" in message_text:
                return MailcowMailboxProvisionResult(
                    status="conflict",
                    detail="Mailbox already exists in remote Mailcow.",
                    created=False,
                    http_status=200,
                    reason="mailbox_exists",
                )
            if "domain" in message_text and any(token in message_text for token in ("missing", "not found", "unknown", "invalid")):
                return MailcowMailboxProvisionResult(
                    status="failed",
                    detail="The selected domain does not exist in remote Mailcow.",
                    created=False,
                    http_status=200,
                    reason="domain_missing",
                )

        return MailcowMailboxProvisionResult(
            status="unexpected_response",
            detail="Mailcow API returned an unrecognized mailbox creation response.",
            created=False,
            http_status=200,
            reason="unexpected_response",
        )

    @staticmethod
    def _normalize_result_entries(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []

    @staticmethod
    def _entry_text(entry: dict[str, Any]) -> str:
        parts: list[str] = []
        msg = entry.get("msg")
        log = entry.get("log")
        for value in (msg, log):
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif value is not None:
                parts.append(str(value))
        return " ".join(parts).lower()
