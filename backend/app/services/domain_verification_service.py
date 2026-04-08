from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

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
        remediation = self._remediation(domain.name, mailcow_result, dns_results)

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
            "remediation": remediation,
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
                return {
                    "status": "missing",
                    "detail": f"No {record_type} records found.",
                    "records": [],
                    "required_configuration": self._required_dns_configuration(name, record_type, []),
                }
            return {
                "status": "configured",
                "detail": f"{record_type} records found.",
                "records": records,
                "required_configuration": self._required_dns_configuration(name, record_type, records),
            }
        except dns.resolver.NXDOMAIN:
            return {
                "status": "missing",
                "detail": f"{name} does not resolve.",
                "records": [],
                "required_configuration": self._required_dns_configuration(name, record_type, []),
            }
        except dns.resolver.NoAnswer:
            return {
                "status": "missing",
                "detail": f"No {record_type} answer returned.",
                "records": [],
                "required_configuration": self._required_dns_configuration(name, record_type, []),
            }
        except dns.exception.DNSException as exc:
            return {
                "status": "failed",
                "detail": f"{record_type} lookup failed: {exc}",
                "records": [],
                "required_configuration": self._required_dns_configuration(name, record_type, []),
            }

    def _resolve_txt_record(self, name: str, required_fragment: str | None) -> dict[str, Any]:
        try:
            answers = dns.resolver.resolve(name, "TXT")
            records = [answer.to_text().strip('"') for answer in answers]
        except dns.resolver.NXDOMAIN:
            return {
                "status": "missing",
                "detail": f"{name} does not resolve.",
                "records": [],
                "required_configuration": self._required_txt_configuration(name, required_fragment, []),
            }
        except dns.resolver.NoAnswer:
            return {
                "status": "missing",
                "detail": "No TXT records returned.",
                "records": [],
                "required_configuration": self._required_txt_configuration(name, required_fragment, []),
            }
        except dns.exception.DNSException as exc:
            return {
                "status": "failed",
                "detail": f"TXT lookup failed: {exc}",
                "records": [],
                "required_configuration": self._required_txt_configuration(name, required_fragment, []),
            }

        if required_fragment is None:
            if records:
                return {
                    "status": "configured",
                    "detail": "TXT record found.",
                    "records": records,
                    "required_configuration": self._required_txt_configuration(name, required_fragment, records),
                }
            return {
                "status": "missing",
                "detail": "No TXT records returned.",
                "records": [],
                "required_configuration": self._required_txt_configuration(name, required_fragment, []),
            }

        for record in records:
            if required_fragment.lower() in record.lower():
                return {
                    "status": "configured",
                    "detail": f"{required_fragment} record found.",
                    "records": records,
                    "required_configuration": self._required_txt_configuration(name, required_fragment, records),
                }
        return {
            "status": "missing",
            "detail": f"{required_fragment} record missing.",
            "records": records,
            "required_configuration": self._required_txt_configuration(name, required_fragment, records),
        }

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

    def _mailcow_host(self) -> str | None:
        if not self.mailcow_client.api_url:
            return None
        parts = urlsplit(self.mailcow_client.api_url)
        return parts.hostname

    def _required_dns_configuration(self, name: str, record_type: str, records: list[str]) -> dict[str, Any]:
        mailcow_host = self._mailcow_host()
        if record_type == "MX":
            return {
                "label": "MX",
                "host": name,
                "type": "MX",
                "expected_value": f"10 {mailcow_host}." if mailcow_host else "10 mail.your-mailcow-host.example.",
                "explanation": "Point MX to the Mailcow host so inbound mail reaches the server.",
                "observed_records": records,
            }
        return {
            "label": record_type,
            "host": name,
            "type": record_type,
            "observed_records": records,
        }

    def _required_txt_configuration(self, name: str, required_fragment: str | None, records: list[str]) -> dict[str, Any]:
        mailcow_host = self._mailcow_host()
        if required_fragment == "v=spf1":
            return {
                "label": "SPF",
                "host": name,
                "type": "TXT",
                "expected_value": f"v=spf1 mx a:{mailcow_host} ~all" if mailcow_host else "v=spf1 mx a:mail.your-mailcow-host.example ~all",
                "explanation": "Authorize the Mailcow host to send mail for this domain.",
                "observed_records": records,
            }
        if name.startswith("dkim._domainkey."):
            return {
                "label": "DKIM",
                "host": name,
                "type": "TXT",
                "expected_value": "Add the DKIM public key generated by Mailcow for this domain.",
                "explanation": "Create the selector TXT record with the Mailcow-generated DKIM public key before sending.",
                "observed_records": records,
            }
        if name.startswith("_dmarc."):
            domain_name = name.removeprefix("_dmarc.")
            return {
                "label": "DMARC",
                "host": name,
                "type": "TXT",
                "expected_value": f"v=DMARC1; p=none; rua=mailto:postmaster@{domain_name}",
                "explanation": "Publish a DMARC policy so recipient systems can evaluate mail alignment and reporting.",
                "observed_records": records,
            }
        return {
            "label": "TXT",
            "host": name,
            "type": "TXT",
            "expected_value": required_fragment or "TXT record required",
            "observed_records": records,
        }

    def _remediation(self, domain_name: str, mailcow_result: Any, dns_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        mailcow_host = self._mailcow_host()
        mailcow_guidance = {
            "status": self._map_mailcow_status(mailcow_result),
            "detail": mailcow_result.detail,
            "action": (
                f"Add {domain_name} in the Mailcow admin before treating it as mail-ready."
                if mailcow_result.status == "not_found"
                else "Fix backend Mailcow connectivity before re-running verification."
            ),
            "mailcow_host": mailcow_host,
        }

        return {
            "mailcow": mailcow_guidance,
            "dns": {
                key: value.get("required_configuration", {})
                for key, value in dns_results.items()
            },
        }
