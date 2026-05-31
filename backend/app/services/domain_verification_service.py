from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import dns.exception
import dns.resolver
from sqlalchemy.orm import Session

from app.models.core import Domain


class DomainVerificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def verify_domain(self, domain: Domain) -> Domain:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        dns_results = self._check_dns(domain.name)
        dns_statuses = {record_type: result["status"] for record_type, result in dns_results.items()}
        missing_requirements = self._missing_requirements(dns_statuses)
        remediation = self._remediation(domain.name, dns_results)

        domain.mx_status = dns_statuses["mx"]
        domain.spf_status = dns_statuses["spf"]
        domain.dkim_status = dns_statuses["dkim"]
        domain.dmarc_status = dns_statuses["dmarc"]
        domain.dns_results = dns_results
        domain.missing_requirements = missing_requirements
        domain.verification_summary = {
            "dns": dns_results,
            "readiness": {
                "status": self._compute_lifecycle(dns_statuses),
                "missing_requirements": missing_requirements,
            },
            "remediation": remediation,
        }
        domain.status = self._compute_lifecycle(dns_statuses)
        domain.last_checked_at = now
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

    def _compute_lifecycle(self, dns_statuses: dict[str, str]) -> str:
        configured_count = sum(1 for status in dns_statuses.values() if status == "configured")
        failed_count = sum(1 for status in dns_statuses.values() if status == "failed")

        if failed_count:
            return "failed"
        if configured_count == len(dns_statuses):
            return "ready"
        if configured_count > 0:
            return "dns_partial"
        return "local_only"

    def _missing_requirements(self, dns_statuses: dict[str, str]) -> list[str]:
        missing: list[str] = []
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

    def _required_dns_configuration(self, name: str, record_type: str, records: list[str]) -> dict[str, Any]:
        if record_type == "MX":
            return {
                "label": "MX",
                "host": name,
                "type": "MX",
                "expected_value": "10 mail.yourdomain.com.",
                "explanation": "Point MX to your mail server so inbound mail reaches the server.",
                "observed_records": records,
            }
        return {
            "label": record_type,
            "host": name,
            "type": record_type,
            "observed_records": records,
        }

    def _required_txt_configuration(self, name: str, required_fragment: str | None, records: list[str]) -> dict[str, Any]:
        if required_fragment == "v=spf1":
            return {
                "label": "SPF",
                "host": name,
                "type": "TXT",
                "expected_value": "v=spf1 include:_spf.google.com ~all",
                "explanation": "Authorize Google Workspace to send mail for this domain.",
                "observed_records": records,
            }
        if name.startswith("dkim._domainkey."):
            return {
                "label": "DKIM",
                "host": name,
                "type": "TXT",
                "expected_value": "Add the DKIM public key from Google Workspace admin for this domain.",
                "explanation": "Create the selector TXT record with the Google Workspace DKIM public key before sending.",
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

    def _remediation(self, domain_name: str, dns_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return {
            "dns": {
                key: value.get("required_configuration", {})
                for key, value in dns_results.items()
            },
        }
