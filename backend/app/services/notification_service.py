from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.campaign import SendLog
from app.models.command_center import OperatorActionLog, OperatorTask
from app.models.core import Mailbox
from app.models.email import Message
from app.models.monitoring import JobLog, NotificationReadState, QualityCheckResult, QualityCheckRun, SystemAlert
from app.models.user import User
from app.services.command_center_service import ACTIVE_TASK_STATUSES


@dataclass
class DerivedNotification:
    id: str
    title: str
    message: str
    severity: str
    source: str
    status: str
    created_at: datetime
    href: str | None = None


def _safe_text(value: str | None, fallback: str, limit: int = 180) -> str:
    text = (value or fallback).strip() or fallback
    blocked_terms = ("password", "secret", "refresh_token", "access_token", "smtp_password", "imap_password")
    if any(term in text.lower() for term in blocked_terms):
        return fallback
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}..."


def _severity_from(value: str | None, default: str = "warning") -> str:
    normalized = (value or "").lower()
    if normalized in {"critical", "error", "failed", "blocked", "dead_letter"}:
        return "critical"
    if normalized in {"warning", "degraded", "skipped"}:
        return "warning"
    if normalized in {"success", "healthy", "ready"}:
        return "success"
    return default


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self, *, user: User, limit: int = 20) -> dict:
        notifications = self._collect_notifications(limit=max(limit * 3, 40))
        read_state = self._read_state(user, [item.id for item in notifications])
        serialized = [
            self._serialize(item, read_state.get(item.id))
            for item in sorted(notifications, key=lambda item: item.created_at, reverse=True)[:limit]
        ]
        return {
            "unread_count": sum(1 for item in notifications if item.id not in read_state),
            "items": serialized,
        }

    def mark_read(self, *, user: User, notification_key: str) -> dict:
        self._mark_keys_read(user=user, keys=[notification_key])
        return {"status": "read", "id": notification_key}

    def mark_all_read(self, *, user: User) -> dict:
        notifications = self._collect_notifications(limit=100)
        self._mark_keys_read(user=user, keys=[item.id for item in notifications])
        return {"status": "read", "count": len(notifications)}

    def _read_state(self, user: User, keys: list[str]) -> dict[str, datetime]:
        if not keys:
            return {}
        rows = (
            self.db.query(NotificationReadState)
            .filter(NotificationReadState.user_id == user.id, NotificationReadState.notification_key.in_(keys))
            .all()
        )
        return {row.notification_key: row.read_at for row in rows}

    def _mark_keys_read(self, *, user: User, keys: list[str]) -> None:
        now = datetime.now(timezone.utc)
        unique_keys = sorted({key for key in keys if key})
        if not unique_keys:
            return
        existing = self._read_state(user, unique_keys)
        for key in unique_keys:
            if key in existing:
                continue
            self.db.add(NotificationReadState(user_id=user.id, notification_key=key, read_at=now))
        self.db.commit()

    def _serialize(self, item: DerivedNotification, read_at: datetime | None) -> dict:
        return {
            "id": item.id,
            "title": item.title,
            "message": item.message,
            "severity": item.severity,
            "source": item.source,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "href": item.href,
            "read_at": read_at.isoformat() if read_at else None,
        }

    def _collect_notifications(self, *, limit: int) -> list[DerivedNotification]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        items: list[DerivedNotification] = []
        items.extend(self._system_alerts(limit))
        items.extend(self._failed_jobs(cutoff, limit))
        items.extend(self._failed_sends(cutoff, limit))
        items.extend(self._blocked_tasks(limit))
        items.extend(self._failed_actions(cutoff, limit))
        items.extend(self._unread_replies(limit))
        items.extend(self._provider_issues(limit))
        items.extend(self._quality_failures(cutoff, limit))
        return sorted(items, key=lambda item: item.created_at, reverse=True)[:limit]

    def _system_alerts(self, limit: int) -> list[DerivedNotification]:
        rows = (
            self.db.query(SystemAlert)
            .filter(SystemAlert.is_active == True, SystemAlert.is_acknowledged == False)
            .order_by(SystemAlert.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            DerivedNotification(
                id=f"alert:{alert.id}",
                title=alert.title,
                message=_safe_text(alert.message, "System alert requires attention."),
                severity=_severity_from(alert.severity),
                source=alert.source or "system",
                status=alert.severity or "info",
                created_at=alert.created_at,
                href="/ops/alerts",
            )
            for alert in rows
            if alert.created_at
        ]

    def _failed_jobs(self, cutoff: datetime, limit: int) -> list[DerivedNotification]:
        rows = (
            self.db.query(JobLog)
            .filter(JobLog.created_at >= cutoff, JobLog.status.in_(["failed", "dead_letter"]))
            .order_by(JobLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            DerivedNotification(
                id=f"job:{job.id}",
                title=f"{job.job_type.replace('_', ' ').title()} job {job.status.replace('_', ' ')}",
                message=_safe_text(job.error_message, "Worker job failed. Open queues for details."),
                severity=_severity_from(job.status),
                source="worker",
                status=job.status,
                created_at=job.created_at,
                href="/ops/jobs",
            )
            for job in rows
            if job.created_at
        ]

    def _failed_sends(self, cutoff: datetime, limit: int) -> list[DerivedNotification]:
        rows = (
            self.db.query(SendLog)
            .filter(SendLog.created_at >= cutoff, SendLog.delivery_status == "failed")
            .order_by(SendLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            DerivedNotification(
                id=f"send:{send.id}",
                title="Email send failed",
                message=_safe_text(send.smtp_response, f"Send to {send.target_email} failed."),
                severity="critical",
                source="sending",
                status="failed",
                created_at=send.created_at,
                href=f"/campaigns" if send.campaign_id else "/send-email",
            )
            for send in rows
            if send.created_at
        ]

    def _blocked_tasks(self, limit: int) -> list[DerivedNotification]:
        now = datetime.now(timezone.utc)
        rows = (
            self.db.query(OperatorTask)
            .filter(or_(OperatorTask.status == "blocked", OperatorTask.status.in_(ACTIVE_TASK_STATUSES) & (OperatorTask.due_at < now)))
            .order_by(OperatorTask.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [
            DerivedNotification(
                id=f"task:{task.id}",
                title="Command Center task needs attention" if task.status == "blocked" else "Command Center task is overdue",
                message=_safe_text(task.description, task.title),
                severity="critical" if task.priority in {"critical", "high"} or task.status == "blocked" else "warning",
                source="command_center",
                status=task.status,
                created_at=task.updated_at or task.created_at,
                href="/command-center",
            )
            for task in rows
            if task.updated_at or task.created_at
        ]

    def _failed_actions(self, cutoff: datetime, limit: int) -> list[DerivedNotification]:
        rows = (
            self.db.query(OperatorActionLog)
            .filter(OperatorActionLog.created_at >= cutoff, OperatorActionLog.result.in_(["failed", "blocked"]))
            .order_by(OperatorActionLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            DerivedNotification(
                id=f"action:{action.id}",
                title=f"{action.source.replace('_', ' ').title()} action {action.result}",
                message=_safe_text(action.message, "Operational action needs attention."),
                severity=_severity_from(action.result),
                source=action.source,
                status=action.result,
                created_at=action.created_at,
                href="/command-center",
            )
            for action in rows
            if action.created_at
        ]

    def _unread_replies(self, limit: int) -> list[DerivedNotification]:
        rows = (
            self.db.query(Message)
            .options(joinedload(Message.thread))
            .filter(Message.direction == "inbound", Message.is_read == False)
            .order_by(Message.received_at.desc().nullslast(), Message.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            DerivedNotification(
                id=f"inbox:{message.id}",
                title="Unread inbox reply",
                message=_safe_text(message.subject, f"New reply from {message.from_email}"),
                severity="info",
                source="inbox",
                status="unread",
                created_at=message.received_at or message.created_at,
                href=f"/inbox?thread={message.thread_id}",
            )
            for message in rows
            if message.received_at or message.created_at
        ]

    def _provider_issues(self, limit: int) -> list[DerivedNotification]:
        rows = (
            self.db.query(Mailbox)
            .filter(
                or_(
                    Mailbox.provider_status.in_(["disabled", "failed", "blocked"]),
                    Mailbox.provider_config_status.in_(["missing", "misconfigured", "failed"]),
                    Mailbox.last_provider_check_status.in_(["failed", "blocked"]),
                    Mailbox.oauth_connection_status.in_(["expired", "error", "needs_reauth"]),
                    Mailbox.smtp_last_check_status.in_(["failed", "blocked"]),
                    Mailbox.inbox_sync_status.in_(["failed", "blocked"]),
                    Mailbox.warmup_status.in_(["failed", "blocked"]),
                )
            )
            .order_by(Mailbox.updated_at.desc())
            .limit(limit)
            .all()
        )
        notifications: list[DerivedNotification] = []
        for mailbox in rows:
            issue = (
                mailbox.last_provider_check_message
                or mailbox.oauth_last_error
                or mailbox.smtp_last_check_message
                or mailbox.inbox_last_error
                or mailbox.warmup_block_reason
                or "Mailbox provider or connectivity requires attention."
            )
            notifications.append(
                DerivedNotification(
                    id=f"mailbox:{mailbox.id}:provider",
                    title=f"Mailbox issue: {mailbox.email}",
                    message=_safe_text(issue, "Mailbox provider or connectivity requires attention."),
                    severity="critical",
                    source=mailbox.provider_type or "mailbox",
                    status=mailbox.last_provider_check_status or mailbox.smtp_last_check_status or mailbox.inbox_sync_status or "blocked",
                    created_at=mailbox.updated_at or mailbox.created_at,
                    href="/mailboxes",
                )
            )
        return notifications

    def _quality_failures(self, cutoff: datetime, limit: int) -> list[DerivedNotification]:
        rows = (
            self.db.query(QualityCheckResult)
            .join(QualityCheckRun, QualityCheckResult.run_id == QualityCheckRun.id)
            .filter(QualityCheckResult.checked_at >= cutoff, QualityCheckResult.status.in_(["failed", "blocked"]))
            .order_by(QualityCheckResult.checked_at.desc())
            .limit(limit)
            .all()
        )
        return [
            DerivedNotification(
                id=f"quality:{result.id}",
                title=f"Quality check {result.status}: {result.name}",
                message=_safe_text(result.message, "Quality Center check needs attention."),
                severity=_severity_from(result.status),
                source="quality_center",
                status=result.status,
                created_at=result.checked_at or result.created_at,
                href=result.href or "/quality-center",
            )
            for result in rows
            if result.checked_at or result.created_at
        ]
