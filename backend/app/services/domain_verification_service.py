from __future__ import annotations

from datetime import datetime
from typing import Any

import dns.exception
import dns.resolver
from sqlalchemy.orm import Session

from app.integrations.mailcow import MailcowClient
from app.models.core import Domain


class DomainVerificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.mailcow_client = MailcowClient()

    def verify_domain(self, domain: Domain) -> Domain:
        now = datetime.utcnow()
        mailcow_result = self.mailcow_client.lookup_domain(domain.name)
        dns_results = self._check_dns(domain.name)
        dns_statuses = {record_type: result["status"] for record_type, result in dns_results.items()}
        missing_requirements = self._missing_requirements(mailcow_result, dns_statuses)

        domain.mailcow_status = self._map_mailcow_status(mailcow_result)
        domain.mailcow_detail = mailcow_result.detail
        domain.mx_status = dns_statuses["mx"]
        domain.spf_status = dns_statuses["spf"]
        domain.dkim_status = dns_statuses["dkim"]
        domain.dmarc_status = dns_statuses["dmarc"]
        domain.dns_results = dns_results
        domain.missing_requirements = missing_requirements
        domain.verification_summary = {
            "mailcow": {
                "status": domain.mailcow_status,
                "detail": mailcow_result.detail,
                "http_status": mailcow_result.http_status,
                "exists": mailcow_result.exists,
            },
            "dns": dns_results,
            "readiness": {
                "status": self._compute_lifecycle(mailcow_result, dns_statuses),
                "missing_requirements": missing_requirements,
            },
        }
        domain.status = self._compute_lifecycle(mailcow_result, dns_statuses)
        domain.last_checked_at = now
        domain.mailcow_last_checked_at = now
        domain.dns_last_checked_at = now
        domain.verification_error = None

        self.db.add(domain)
        self.db.commit()
        self.db.refresh(domain)
        return domain

    def _check_dns(self, domain_name: str) -> dict[str, dict[str, Any]]:
        return {
            "mx": self._resolve_record(domain_name, "MX"),
            "spf": self._resolve_txt_record(domain_name, "v=spf1"),
            "dkim": self._resolve_txt_record(f"dkim._domainkey.{domain_name}", None),
            "dmarc": self._resolve_txt_record(f"_dmarc.{domain_name}", "v=DMARC1"),
        }

    def _resolve_record(self, name: str, record_type: str) -> dict[str, Any]:
        try:
            answers = dns.resolver.resolve(name, record_type)
            records = [str(answer).strip() for answer in answers]
            if not records:
                return {"status": "missing", "detail": f"No {record_type} records found.", "records": []}
            return {"status": "configured", "detail": f"{record_type} records found.", "records": records}
        except dns.resolver.NXDOMAIN:
            return {"status": "missing", "detail": f"{name} does not resolve.", "records": []}
        except dns.resolver.NoAnswer:
            return {"status": "missing", "detail": f"No {record_type} answer returned.", "records": []}
        except dns.exception.DNSException as exc:
            return {"status": "failed", "detail": f"{record_type} lookup failed: {exc}", "records": []}

    def _resolve_txt_record(self, name: str, required_fragment: str | None) -> dict[str, Any]:
        try:
            answers = dns.resolver.resolve(name, "TXT")
            records = [answer.to_text().strip('"') for answer in answers]
        except dns.resolver.NXDOMAIN:
            return {"status": "missing", "detail": f"{name} does not resolve.", "records": []}
        except dns.resolver.NoAnswer:
            return {"status": "missing", "detail": "No TXT records returned.", "records": []}
        except dns.exception.DNSException as exc:
            return {"status": "failed", "detail": f"TXT lookup failed: {exc}", "records": []}

        if required_fragment is None:
            if records:
                return {"status": "configured", "detail": "TXT record found.", "records": records}
            return {"status": "missing", "detail": "No TXT records returned.", "records": []}

        for record in records:
            if required_fragment.lower() in record.lower():
                return {"status": "configured", "detail": f"{required_fragment} record found.", "records": records}
        return {"status": "missing", "detail": f"{required_fragment} record missing.", "records": records}

    def _map_mailcow_status(self, result: Any) -> str:
        if result.exists:
            return "verified"
        if result.status == "not_found":
            return "missing"
        if result.status in {"unconfigured", "unauthorized", "unreachable", "unexpected_response"}:
            return "blocked"
        return "failed"

    def _compute_lifecycle(self, mailcow_result: Any, dns_statuses: dict[str, str]) -> str:
        if mailcow_result.status in {"unconfigured", "unauthorized", "unreachable", "unexpected_response"}:
            return "blocked"
        if mailcow_result.status == "error":
            return "failed"
        if not mailcow_result.exists:
            return "local_only"

        configured_count = sum(1 for status in dns_statuses.values() if status == "configured")
        failed_count = sum(1 for status in dns_statuses.values() if status == "failed")

        if failed_count:
            return "failed"
        if configured_count == len(dns_statuses):
            return "ready"
        if configured_count > 0:
            return "dns_partial"
        return "mailcow_verified"

    def _missing_requirements(self, mailcow_result: Any, dns_statuses: dict[str, str]) -> list[str]:
        missing: list[str] = []
        if not mailcow_result.exists:
            if mailcow_result.status == "not_found":
                missing.append("Domain is not present in remote Mailcow.")
            elif mailcow_result.status == "unconfigured":
                missing.append("Mailcow API credentials are not configured on the backend.")
            elif mailcow_result.status == "unauthorized":
                missing.append("Mailcow API rejected the configured backend credentials.")
            elif mailcow_result.status == "unreachable":
                missing.append("Mailcow API is unreachable from the backend.")
            else:
                missing.append("Mailcow domain verification did not complete successfully.")

        labels = {
            "mx": "MX record",
            "spf": "SPF record",
            "dkim": "DKIM record",
            "dmarc": "DMARC record",
        }
        for key, status in dns_statuses.items():
            if status != "configured":
                missing.append(f"{labels[key]} is not fully configured.")
        return missing
