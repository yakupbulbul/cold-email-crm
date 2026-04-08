from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


@dataclass
class MailcowDomainLookup:
    status: str
    detail: str
    exists: bool
    http_status: int | None = None


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

    def _request(self, method: str, path: str) -> httpx.Response:
        if not self.api_url:
            raise MailcowError("Mailcow API URL is not configured")
        with httpx.Client(timeout=self.timeout, verify=self.verify_ssl) as client:
            response = client.request(
                method=method,
                url=f"{self.api_url}/{path.lstrip('/')}",
                headers=self._headers(),
            )
        return response

    def check_health(self) -> MailcowHealth:
        if not self.configured:
            return MailcowHealth(
                status="unknown",
                detail="Mailcow API credentials are not configured for this environment.",
                reason="unconfigured",
            )

        try:
            response = self._request("GET", "/get/status/containers")
        except httpx.HTTPError as exc:
            return MailcowHealth(
                status="failed",
                detail=f"Mailcow API unreachable: {exc}",
                reason="unreachable",
            )
        except MailcowError as exc:
            return MailcowHealth(status="failed", detail=str(exc), reason="misconfigured")

        if response.status_code == 200:
            return MailcowHealth(
                status="healthy",
                detail="Mailcow API responded successfully.",
                http_status=200,
                reason="healthy",
            )
        if response.status_code in {401, 403}:
            return MailcowHealth(
                status="failed",
                detail="Mailcow API rejected the configured credentials.",
                http_status=response.status_code,
                reason="unauthorized",
            )
        return MailcowHealth(
            status="degraded",
            detail=f"Mailcow API returned an unexpected status code ({response.status_code}).",
            http_status=response.status_code,
            reason="unexpected_response",
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
            )
        try:
            response = self._request("GET", f"/get/domain/{domain_name}")
        except httpx.HTTPError as exc:
            return MailcowDomainLookup(
                status="unreachable",
                detail=f"Mailcow API unreachable: {exc}",
                exists=False,
            )
        except MailcowError as exc:
            return MailcowDomainLookup(
                status="error",
                detail=str(exc),
                exists=False,
            )

        if response.status_code in {401, 403}:
            return MailcowDomainLookup(
                status="unauthorized",
                detail="Mailcow API rejected the configured credentials.",
                exists=False,
                http_status=response.status_code,
            )
        if response.status_code == 200:
            payload: Any = response.json()
            exists = bool(payload)
            return MailcowDomainLookup(
                status="verified" if exists else "not_found",
                detail="Domain found in remote Mailcow." if exists else "Domain not found in remote Mailcow.",
                exists=exists,
                http_status=200,
            )
        if response.status_code == 404:
            return MailcowDomainLookup(
                status="not_found",
                detail="Domain not found in remote Mailcow.",
                exists=False,
                http_status=404,
            )
        return MailcowDomainLookup(
            status="unexpected_response",
            detail=f"Mailcow API returned an unexpected status code ({response.status_code}).",
            exists=False,
            http_status=response.status_code,
        )
