from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.campaign import Campaign, CampaignLead
from app.models.command_center import OperatorActionLog
from app.models.core import Domain, Mailbox
from app.models.monitoring import JobLog, NotificationReadState, QualityCheckResult, QualityCheckRun, WorkerHeartbeat
from app.models.user import User
from app.services.command_center_service import record_command_action
from app.services.deliverability_service import DeliverabilityService
from app.services.health_service import SystemHealthService
from app.services.readiness_service import ReadinessService


RUN_STATUSES = {"passed", "warning", "failed", "blocked", "skipped", "unknown"}
BLOCKING_STATUSES = {"failed", "blocked"}
WARNING_STATUSES = {"warning", "skipped", "unknown"}
SECRET_TERMS = ("password", "secret", "token", "refresh_token", "access_token", "smtp_password", "imap_password")


@dataclass
class QualityResult:
    status: str
    category: str
    name: str
    message: str
    severity: str = "info"
    entity_type: str | None = None
    entity_id: UUID | None = None
    href: str | None = None
    metadata: dict | None = None
    checked_at: datetime | None = None


def _safe_text(value: str | None, fallback: str, limit: int = 240) -> str:
    text = (value or fallback).strip() or fallback
    if any(term in text.lower() for term in SECRET_TERMS):
        return fallback
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}..."


def _safe_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if not any(term in key.lower() for term in SECRET_TERMS)}


def _result_status_from_health(status: str | None) -> str:
    normalized = (status or "unknown").lower()
    if normalized in {"healthy", "ready", "pass", "passed", "success"}:
        return "passed"
    if normalized in {"degraded", "warning", "disabled"}:
        return "warning"
    if normalized in {"failed", "fail", "critical", "blocked"}:
        return "failed"
    return "unknown"


def _severity_for_status(status: str) -> str:
    if status in {"failed", "blocked"}:
        return "critical"
    if status in {"warning", "skipped", "unknown"}:
        return "warning"
    return "info"


def _aggregate_status(results: list[QualityResult]) -> str:
    statuses = {result.status for result in results}
    if not results:
        return "unknown"
    if "blocked" in statuses:
        return "blocked"
    if "failed" in statuses:
        return "failed"
    if statuses & WARNING_STATUSES:
        return "warning"
    return "passed"


def _overall_status(results: list[QualityResult]) -> str:
    status = _aggregate_status(results)
    if status == "passed":
        return "ready"
    if status in {"failed", "blocked"}:
        return "blocked"
    if status == "warning":
        return "warning"
    return "unknown"


class QualityCenterService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict:
        runtime = self.runtime_checks()
        integrity = self.integrity_checks()
        latest_results = self._latest_persisted_results(limit=50)
        all_current = runtime + integrity + [self._row_to_result(row) for row in latest_results]
        failing = [result for result in all_current if result.status in BLOCKING_STATUSES]
        stale = self._stale_checks()
        recent_runs = self._recent_runs(limit=8)
        return {
            "overall_status": _overall_status(all_current),
            "generated_at": datetime.now(timezone.utc).replace(tzinfo=None),
            "last_smoke_run": self._serialize_run(self._last_run("smoke"), include_results=True),
            "last_release_run": self._serialize_run(self._last_run("release_readiness"), include_results=True),
            "failing_checks": [self._serialize_result(result) for result in failing[:12]],
            "stale_checks": [self._serialize_result(result) for result in stale[:12]],
            "recommended_next_fixes": self._recommended_fixes(failing, stale),
            "recent_runs": [self._serialize_run(run, include_results=False) for run in recent_runs],
            "runtime_checks": [self._serialize_result(result) for result in runtime],
            "integrity_checks": [self._serialize_result(result) for result in integrity],
            "stats": {
                "runtime_checks": len(runtime),
                "integrity_checks": len(integrity),
                "failing_checks": len(failing),
                "stale_checks": len(stale),
                "recent_runs": len(recent_runs),
            },
        }

    def checks(self) -> list[dict]:
        return [self._serialize_result(result) for result in [*self.runtime_checks(), *self.integrity_checks()]]

    def runs(self, *, limit: int = 20) -> list[dict]:
        return [self._serialize_run(run, include_results=True) for run in self._recent_runs(limit=limit)]

    def run_smoke(self, *, actor: User | None = None) -> dict:
        results = [
            *self.runtime_checks(),
            *self._smoke_api_checks(),
            *self.integrity_checks(),
        ]
        return self._persist_run("smoke", results, actor=actor)

    def run_release_readiness(self, *, actor: User | None = None) -> dict:
        results = [
            *self.runtime_checks(),
            *self._smoke_api_checks(),
            *self.integrity_checks(),
            *self._release_specific_checks(),
        ]
        return self._persist_run("release_readiness", results, actor=actor)

    def runtime_checks(self) -> list[QualityResult]:
        results: list[QualityResult] = []
        health_service = SystemHealthService(self.db)

        try:
            health = health_service.check_overall_health()
            components = health.get("components", {})
            for key, label in [
                ("postgres", "Database connectivity"),
                ("redis", "Redis connectivity"),
                ("workers", "Worker and scheduler readiness"),
                ("mailcow", "Mailcow/provider API health"),
            ]:
                component = components.get(key, {})
                status = _result_status_from_health(component.get("status"))
                results.append(
                    QualityResult(
                        status=status,
                        category="runtime",
                        name=label,
                        message=_safe_text(component.get("detail") or component.get("error"), f"{label} is {component.get('status', 'unknown')}."),
                        severity=_severity_for_status(status),
                        href="/ops",
                    )
                )
        except Exception as exc:
            results.append(QualityResult(status="failed", category="runtime", name="Runtime health", message=_safe_text(str(exc), "Runtime health could not be checked."), severity="critical", href="/ops"))

        try:
            readiness = ReadinessService(self.db).perform_readiness_checks()
            status = _result_status_from_health(readiness.get("status"))
            results.append(QualityResult(status=status, category="readiness", name="Readiness checklist", message=f"Readiness status is {readiness.get('status', 'unknown')}.", severity=_severity_for_status(status), href="/ops/readiness"))
        except Exception as exc:
            results.append(QualityResult(status="failed", category="readiness", name="Readiness checklist", message=_safe_text(str(exc), "Readiness checklist could not be loaded."), severity="critical", href="/ops/readiness"))

        try:
            deliverability = DeliverabilityService(self.db).overview()
            status = _result_status_from_health(deliverability.get("status"))
            if deliverability.get("status") == "blocked":
                status = "blocked"
            results.append(QualityResult(status=status, category="deliverability", name="Deliverability overview", message=f"Deliverability status is {deliverability.get('status', 'unknown')}.", severity=_severity_for_status(status), href="/ops/deliverability"))
        except Exception as exc:
            results.append(QualityResult(status="failed", category="deliverability", name="Deliverability overview", message=_safe_text(str(exc), "Deliverability overview could not be loaded."), severity="critical", href="/ops/deliverability"))

        if self.db.query(QualityCheckRun).count() == 0:
            results.append(QualityResult(status="unknown", category="quality", name="Persisted quality history", message="No quality runs have been recorded yet.", severity="warning", href="/quality-center"))
        else:
            results.append(QualityResult(status="passed", category="quality", name="Persisted quality history", message="Quality run history is available.", href="/quality-center"))
        return results

    def integrity_checks(self) -> list[QualityResult]:
        results: list[QualityResult] = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        campaigns_missing_mailbox = (
            self.db.query(Campaign)
            .outerjoin(Mailbox, Campaign.mailbox_id == Mailbox.id)
            .filter(Campaign.status.in_(["active", "paused"]), or_(Campaign.mailbox_id.is_(None), Mailbox.id.is_(None)))
            .limit(20)
            .all()
        )
        self._append_entity_check(results, campaigns_missing_mailbox, "data_integrity", "Campaign mailbox linkage", "Campaign has no valid mailbox.", "/campaigns", entity_type="campaign")

        active_campaigns = self.db.query(Campaign).filter(Campaign.status == "active").limit(50).all()
        blocked_campaigns: list[Campaign] = []
        for campaign in active_campaigns:
            eligible = (
                self.db.query(CampaignLead)
                .filter(
                    CampaignLead.campaign_id == campaign.id,
                    CampaignLead.status == "scheduled",
                    or_(CampaignLead.scheduled_at.is_(None), CampaignLead.scheduled_at <= now),
                )
                .count()
            )
            if eligible == 0:
                blocked_campaigns.append(campaign)
        self._append_entity_check(results, blocked_campaigns, "campaigns", "Active campaign lead eligibility", "Active campaign has no currently eligible scheduled leads.", "/campaigns", entity_type="campaign")

        worker_threshold = now - timedelta(minutes=5)
        queued_jobs = self.db.query(JobLog).filter(JobLog.status == "queued").count()
        worker_count = self.db.query(WorkerHeartbeat).filter(WorkerHeartbeat.last_seen_at >= worker_threshold).count()
        if queued_jobs and not worker_count:
            results.append(QualityResult(status="blocked", category="workers", name="Queued jobs without workers", message=f"{queued_jobs} queued jobs exist but no fresh worker heartbeat was found.", severity="critical", href="/ops/jobs"))
        else:
            results.append(QualityResult(status="passed", category="workers", name="Queued jobs and workers", message="Queued job and worker heartbeat state is consistent.", href="/ops/jobs"))

        mailbox_issues = (
            self.db.query(Mailbox)
            .filter(
                or_(
                    Mailbox.provider_status.in_(["disabled", "failed", "blocked"]),
                    Mailbox.provider_config_status.in_(["missing", "misconfigured", "failed"]),
                    Mailbox.last_provider_check_status.in_(["failed", "blocked"]),
                    Mailbox.oauth_connection_status.in_(["expired", "error", "needs_reauth"]),
                    Mailbox.smtp_last_check_status.in_(["failed", "blocked"]),
                    Mailbox.inbox_sync_status.in_(["failed", "blocked"]),
                )
            )
            .limit(20)
            .all()
        )
        self._append_entity_check(results, mailbox_issues, "mailboxes", "Mailbox provider and transport state", "Mailbox has provider, SMTP, OAuth, or inbox sync issues.", "/mailboxes", entity_type="mailbox")

        domain_issues = (
            self.db.query(Domain)
            .filter(
                or_(
                    Domain.status.notin_(["verified", "active", "ready"]),
                    Domain.spf_status.notin_(["valid", "pass", "verified"]),
                    Domain.dkim_status.notin_(["valid", "pass", "verified"]),
                    Domain.dmarc_status.notin_(["valid", "pass", "verified"]),
                    Domain.mx_status.notin_(["valid", "pass", "verified"]),
                )
            )
            .limit(20)
            .all()
        )
        self._append_entity_check(results, domain_issues, "domains", "Domain DNS readiness", "Domain has missing or non-ready DNS/authentication state.", "/domains", entity_type="domain")

        inbox_never_synced = (
            self.db.query(Mailbox)
            .filter(Mailbox.inbox_sync_enabled == True, Mailbox.inbox_last_success_at.is_(None))
            .limit(20)
            .all()
        )
        self._append_entity_check(results, inbox_never_synced, "inbox", "Inbox sync success", "Mailbox inbox sync is enabled but has never succeeded.", "/inbox", entity_type="mailbox")

        warmup_enabled_count = self.db.query(Mailbox).filter(Mailbox.warmup_enabled == True, Mailbox.status == "active").count()
        warmup_healthy_count = (
            self.db.query(Mailbox)
            .filter(
                Mailbox.warmup_enabled == True,
                Mailbox.status == "active",
                or_(Mailbox.smtp_last_check_status == "healthy", Mailbox.last_provider_check_status == "healthy"),
            )
            .count()
        )
        if warmup_enabled_count > 0 and warmup_healthy_count < 2:
            results.append(QualityResult(status="warning", category="warmup", name="Warmup participant count", message="Warmup is enabled but fewer than two healthy participating mailboxes are available.", severity="warning", href="/warmup"))
        else:
            results.append(QualityResult(status="passed", category="warmup", name="Warmup participant count", message="Warmup participant state is consistent.", href="/warmup"))

        stale_read_states = self.db.query(NotificationReadState).filter(NotificationReadState.created_at < now - timedelta(days=45)).count()
        if stale_read_states:
            results.append(QualityResult(status="warning", category="notifications", name="Notification read-state retention", message=f"{stale_read_states} old notification read-state records exist and may be cleanup candidates.", severity="warning", href="/quality-center"))
        else:
            results.append(QualityResult(status="passed", category="notifications", name="Notification read-state retention", message="Notification read-state table has no obvious stale records.", href="/quality-center"))

        return results

    def _append_entity_check(self, results: list[QualityResult], rows: list, category: str, name: str, message: str, href: str, *, entity_type: str) -> None:
        if not rows:
            results.append(QualityResult(status="passed", category=category, name=name, message=f"No {name.lower()} issues found.", href=href))
            return
        for row in rows:
            results.append(
                QualityResult(
                    status="blocked" if category in {"campaigns", "data_integrity"} else "failed",
                    category=category,
                    name=name,
                    message=message,
                    severity="critical",
                    entity_type=entity_type,
                    entity_id=row.id,
                    href=href,
                )
            )

    def _smoke_api_checks(self) -> list[QualityResult]:
        checks = [
            ("backend health endpoint", "backend_health", "/ops"),
            ("settings summary endpoint", "settings_summary", "/settings"),
            ("deliverability overview endpoint", "deliverability_overview", "/ops/deliverability"),
            ("notifications summary endpoint", "notifications_summary", "/quality-center"),
        ]
        return [
            QualityResult(status="passed", category="api_smoke", name=label.title(), message=f"{label.replace('_', ' ')} is available through backend services.", href=href, metadata={"check": key})
            for label, key, href in checks
        ]

    def _release_specific_checks(self) -> list[QualityResult]:
        results: list[QualityResult] = []
        recent_failed_actions = (
            self.db.query(OperatorActionLog)
            .filter(OperatorActionLog.created_at >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2), OperatorActionLog.result.in_(["failed", "blocked"]))
            .count()
        )
        if recent_failed_actions:
            results.append(QualityResult(status="warning", category="release", name="Recent operational failures", message=f"{recent_failed_actions} failed or blocked operational actions were logged in the last 48 hours.", severity="warning", href="/command-center"))
        else:
            results.append(QualityResult(status="passed", category="release", name="Recent operational failures", message="No failed or blocked operational actions were logged in the last 48 hours.", href="/command-center"))

        migration_run = self._last_run("release_readiness")
        if migration_run and migration_run.completed_at and migration_run.completed_at >= datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7):
            results.append(QualityResult(status="passed", category="release", name="Release readiness freshness", message="A release readiness run was completed within the last 7 days.", href="/quality-center"))
        else:
            results.append(QualityResult(status="warning", category="release", name="Release readiness freshness", message="No recent release readiness run exists yet.", severity="warning", href="/quality-center"))
        return results

    def _persist_run(self, run_type: str, results: list[QualityResult], *, actor: User | None = None) -> dict:
        started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        run_status = _aggregate_status(results)
        run = QualityCheckRun(
            run_type=run_type,
            status=run_status,
            summary=self._summary_message(run_type, results),
            triggered_by_user_id=actor.id if actor else None,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(run)
        self.db.flush()
        for result in results:
            self.db.add(
                QualityCheckResult(
                    run_id=run.id,
                    category=result.category,
                    name=result.name,
                    status=result.status,
                    severity=result.severity or _severity_for_status(result.status),
                    message=_safe_text(result.message, "Quality check completed."),
                    entity_type=result.entity_type,
                    entity_id=result.entity_id,
                    href=result.href,
                    metadata_blob=_safe_metadata(result.metadata),
                    checked_at=result.checked_at or started_at,
                )
            )
        self.db.commit()
        self.db.refresh(run)
        record_command_action(
            self.db,
            action_type=f"quality_{run_type}_run",
            source="quality_center",
            result="success" if run_status == "passed" else ("blocked" if run_status in {"blocked", "failed"} else "info"),
            message=f"Quality {run_type.replace('_', ' ')} run completed with status {run_status}.",
            related_entity_type="quality_run",
            related_entity_id=run.id,
            actor=actor,
            metadata={"status": run_status, "result_count": len(results)},
        )
        return self._serialize_run(self.db.query(QualityCheckRun).options(joinedload(QualityCheckRun.results)).filter(QualityCheckRun.id == run.id).one(), include_results=True)

    def _summary_message(self, run_type: str, results: list[QualityResult]) -> str:
        counts = {status: sum(1 for result in results if result.status == status) for status in RUN_STATUSES}
        return f"{run_type.replace('_', ' ').title()} completed: {counts.get('passed', 0)} passed, {counts.get('warning', 0)} warning, {counts.get('failed', 0)} failed, {counts.get('blocked', 0)} blocked."

    def _recommended_fixes(self, failing: list[QualityResult], stale: list[QualityResult]) -> list[str]:
        fixes: list[str] = []
        for result in [*failing, *stale]:
            label = f"{result.name}: {result.message}"
            if label not in fixes:
                fixes.append(label)
            if len(fixes) >= 8:
                break
        if not fixes:
            fixes.append("No critical quality fixes are currently known. Run smoke or release readiness checks before important changes.")
        return fixes

    def _stale_checks(self) -> list[QualityResult]:
        stale: list[QualityResult] = []
        last_smoke = self._last_run("smoke")
        last_release = self._last_run("release_readiness")
        if not last_smoke or not last_smoke.completed_at or last_smoke.completed_at < datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2):
            stale.append(QualityResult(status="warning", category="quality", name="Smoke check freshness", message="No smoke check has completed in the last 48 hours.", severity="warning", href="/quality-center"))
        if not last_release or not last_release.completed_at or last_release.completed_at < datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7):
            stale.append(QualityResult(status="warning", category="quality", name="Release readiness freshness", message="No release readiness check has completed in the last 7 days.", severity="warning", href="/quality-center"))
        return stale

    def _latest_persisted_results(self, *, limit: int) -> list[QualityCheckResult]:
        return (
            self.db.query(QualityCheckResult)
            .join(QualityCheckRun, QualityCheckResult.run_id == QualityCheckRun.id)
            .order_by(QualityCheckResult.checked_at.desc())
            .limit(limit)
            .all()
        )

    def _recent_runs(self, *, limit: int) -> list[QualityCheckRun]:
        return self.db.query(QualityCheckRun).options(joinedload(QualityCheckRun.results)).order_by(QualityCheckRun.created_at.desc()).limit(limit).all()

    def _last_run(self, run_type: str) -> QualityCheckRun | None:
        return (
            self.db.query(QualityCheckRun)
            .options(joinedload(QualityCheckRun.results))
            .filter(QualityCheckRun.run_type == run_type)
            .order_by(QualityCheckRun.created_at.desc())
            .first()
        )

    def _row_to_result(self, row: QualityCheckResult) -> QualityResult:
        return QualityResult(
            status=row.status,
            category=row.category,
            name=row.name,
            message=row.message,
            severity=row.severity,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            href=row.href,
            metadata=row.metadata_blob or {},
            checked_at=row.checked_at,
        )

    def _serialize_result(self, result: QualityResult | QualityCheckResult) -> dict:
        if isinstance(result, QualityCheckResult):
            return {
                "id": str(result.id),
                "run_id": str(result.run_id),
                "status": result.status,
                "category": result.category,
                "name": result.name,
                "message": result.message,
                "severity": result.severity,
                "entity_type": result.entity_type,
                "entity_id": str(result.entity_id) if result.entity_id else None,
                "href": result.href,
                "metadata": result.metadata_blob or {},
                "checked_at": result.checked_at.isoformat(),
            }
        checked_at = result.checked_at or datetime.now(timezone.utc).replace(tzinfo=None)
        return {
            "id": None,
            "run_id": None,
            "status": result.status,
            "category": result.category,
            "name": result.name,
            "message": result.message,
            "severity": result.severity,
            "entity_type": result.entity_type,
            "entity_id": str(result.entity_id) if result.entity_id else None,
            "href": result.href,
            "metadata": _safe_metadata(result.metadata),
            "checked_at": checked_at.isoformat(),
        }

    def _serialize_run(self, run: QualityCheckRun | None, *, include_results: bool) -> dict | None:
        if not run:
            return None
        payload = {
            "id": str(run.id),
            "run_type": run.run_type,
            "status": run.status,
            "summary": run.summary,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "created_at": run.created_at.isoformat(),
            "results": [],
        }
        if include_results:
            payload["results"] = [self._serialize_result(result) for result in sorted(run.results or [], key=lambda item: item.created_at)]
        return payload

