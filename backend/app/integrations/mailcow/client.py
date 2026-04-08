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
            )

        try:
            response = self._request("GET", "/get/status/containers")
        except httpx.HTTPError as exc:
            return MailcowHealth(status="failed", detail=f"Mailcow API unreachable: {exc}")
        except MailcowError as exc:
            return MailcowHealth(status="failed", detail=str(exc))

        if response.status_code == 200:
            return MailcowHealth(status="healthy", detail="Mailcow API responded successfully.", http_status=200)
        if response.status_code in {401, 403}:
            return MailcowHealth(
                status="failed",
                detail="Mailcow API rejected the configured credentials.",
                http_status=response.status_code,
            )
        return MailcowHealth(
            status="degraded",
            detail=f"Mailcow API returned an unexpected status code ({response.status_code}).",
            http_status=response.status_code,
        )

    def domain_exists(self, domain_name: str) -> bool | None:
        if not self.configured:
            return None
        try:
            response = self._request("GET", f"/get/domain/{domain_name}")
        except (httpx.HTTPError, MailcowError):
            return None
        if response.status_code == 200:
            payload: Any = response.json()
            return bool(payload)
        return None
