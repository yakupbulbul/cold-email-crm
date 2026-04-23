import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.core import Mailbox
from app.models.monitoring import JobLog
from app.models.warmup import WarmupEvent, WarmupPair, WarmupSetting
from app.schemas.email import SendEmailRequest
from app.services.health_service import SystemHealthService
from app.services.mail_provider_service import MailProviderRegistry, ProviderUnavailableError
from app.services.smtp_service import SMTPManagerService, SMTPServiceError

WARMUP_INTERVAL_SECONDS = 900
SCHEDULER_STALE_AFTER_SECONDS = WARMUP_INTERVAL_SECONDS * 2


class WarmupPlanner:
    @staticmethod
    def get_daily_limit(mailbox: Mailbox) -> int:
        days_active = (datetime.now(timezone.utc).replace(tzinfo=None) - mailbox.created_at).days
        if days_active <= 3:
            return 5
        if days_active <= 7:
            return random.randint(8, 12)
        if days_active <= 14:
            return random.randint(15, 20)
        return min(30, mailbox.daily_send_limit)

    @staticmethod
    def next_run_at(now: datetime | None = None) -> datetime:
        current = now or datetime.now(timezone.utc).replace(tzinfo=None)
        interval_minutes = max(WARMUP_INTERVAL_SECONDS // 60, 1)
        next_boundary_minute = ((current.minute // interval_minutes) + 1) * interval_minutes
        if next_boundary_minute >= 60:
            return current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return current.replace(minute=next_boundary_minute, second=0, microsecond=0)


class WarmupService:
    def __init__(self, db: Session):
        self.db = db
        self.smtp = SMTPManagerService(db)
        self.providers = MailProviderRegistry(db)

    def get_or_create_settings(self) -> WarmupSetting:
        setting = self.db.query(WarmupSetting).order_by(WarmupSetting.created_at.asc()).first()
        if setting:
            return setting
        setting = WarmupSetting(is_enabled=False)
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def set_global_enabled(self, enabled: bool) -> WarmupSetting:
        setting = self.get_or_create_settings()
        setting.is_enabled = enabled
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        self.sync_pairs()
        return setting

    def set_mailbox_participation(self, mailbox_id: str, warmup_enabled: bool) -> Mailbox:
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if not mailbox:
            raise ValueError("Mailbox not found")
        mailbox.warmup_enabled = warmup_enabled
        self._refresh_mailbox_warmup_state(mailbox)
        self.db.add(mailbox)
        self.db.commit()
        self.sync_pairs()
        self.db.refresh(mailbox)
        return mailbox

    def get_status_payload(self) -> dict:
        setting = self.get_or_create_settings()
        worker_status = SystemHealthService(self.db).check_worker_health()
        scheduler_status = self._scheduler_status()
        mailboxes = self._mailbox_status_rows()
        self.sync_pairs(commit=False)

        active_pairs = (
            self.db.query(WarmupPair)
            .options(joinedload(WarmupPair.sender), joinedload(WarmupPair.recipient))
            .filter(WarmupPair.is_active == True)
            .all()
        )
        successful_sends_today, failed_sends_today = self._today_send_counts()
        health_percent = self._compute_health_percent(mailboxes, successful_sends_today, failed_sends_today)
        blockers = self._collect_blockers(setting.is_enabled, worker_status, scheduler_status, mailboxes)

        latest_completed = (
            self.db.query(JobLog)
            .filter(JobLog.job_type == "warmup_cycle", JobLog.status == "completed")
            .order_by(JobLog.finished_at.desc().nullslast(), JobLog.created_at.desc())
            .first()
        )

        return {
            "global_status": "enabled" if setting.is_enabled else "paused",
            "worker_status": worker_status,
            "scheduler_status": scheduler_status,
            "inboxes_warming_count": len([m for m in mailboxes if m["warmup_enabled"]]),
            "eligible_mailboxes_count": len([m for m in mailboxes if m["warmup_status"] == "ready"]),
            "active_pairs_count": len(active_pairs),
            "successful_sends_today": successful_sends_today,
            "failed_sends_today": failed_sends_today,
            "health_percent": health_percent,
            "blockers": blockers,
            "next_action": self._next_action(setting.is_enabled, worker_status, scheduler_status, mailboxes, len(active_pairs)),
            "last_run_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
            "next_run_at": self._next_run_at(setting.is_enabled, worker_status, scheduler_status, mailboxes),
            "mailboxes": mailboxes,
        }

    def get_pairs_payload(self) -> list[dict]:
        self.sync_pairs(commit=False)
        next_run = WarmupPlanner.next_run_at()
        pairs = (
            self.db.query(WarmupPair)
            .options(joinedload(WarmupPair.sender), joinedload(WarmupPair.recipient))
            .filter(WarmupPair.is_active == True)
            .order_by(WarmupPair.updated_at.desc())
            .all()
        )
        return [
            {
                "id": str(pair.id),
                "sender_mailbox_id": str(pair.sender_mailbox_id),
                "recipient_mailbox_id": str(pair.recipient_mailbox_id),
                "sender_email": pair.sender.email,
                "recipient_email": pair.recipient.email,
                "state": pair.state,
                "last_send_at": pair.last_sent_at.isoformat() if pair.last_sent_at else None,
                "next_scheduled_at": (pair.next_scheduled_at or next_run).isoformat() if pair.is_active else None,
                "last_result": pair.last_result,
                "last_error": pair.last_error,
                "daily_sent_count": self._pair_daily_sent_count(pair.sender_mailbox_id, pair.recipient_mailbox_id),
                "daily_limit": WarmupPlanner.get_daily_limit(pair.sender),
            }
            for pair in pairs
        ]

    def get_logs_payload(self, limit: int = 50) -> list[dict]:
        events = (
            self.db.query(WarmupEvent)
            .options(joinedload(WarmupEvent.mailbox), joinedload(WarmupEvent.recipient_mailbox))
            .order_by(WarmupEvent.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(event.id),
                "pair_id": str(event.pair_id) if event.pair_id else None,
                "sender_mailbox_id": str(event.mailbox_id),
                "recipient_mailbox_id": str(event.recipient_mailbox_id) if event.recipient_mailbox_id else None,
                "sender_email": event.mailbox.email if event.mailbox else None,
                "recipient_email": event.recipient_mailbox.email if event.recipient_mailbox else event.target_email,
                "timestamp": event.created_at.isoformat() if event.created_at else None,
                "event_type": event.event_type,
                "status": event.status,
                "error_category": event.error_category,
                "result_detail": event.result_detail,
                "target_email": event.target_email,
                "subject": event.subject,
                "scheduled_for": event.scheduled_for.isoformat() if event.scheduled_for else None,
                "sent_at": event.sent_at.isoformat() if event.sent_at else None,
            }
            for event in events
        ]

    def sync_pairs(self, *, commit: bool = True) -> None:
        setting = self.get_or_create_settings()
        mailboxes = self.db.query(Mailbox).all()
        mailbox_rows = [self._refresh_mailbox_warmup_state(mailbox) for mailbox in mailboxes]
        eligible_ids = {row["mailbox_uuid"] for row in mailbox_rows if row["warmup_status"] == "ready"}
        next_run = WarmupPlanner.next_run_at()

        existing_pairs = {
            (pair.sender_mailbox_id, pair.recipient_mailbox_id): pair
            for pair in self.db.query(WarmupPair).all()
        }
        desired_pairs = set()
        if setting.is_enabled and len(eligible_ids) >= 2:
            for sender_id in eligible_ids:
                for recipient_id in eligible_ids:
                    if sender_id == recipient_id:
                        continue
                    desired_pairs.add((sender_id, recipient_id))

        for key, pair in existing_pairs.items():
            should_be_active = key in desired_pairs
            pair.is_active = should_be_active
            pair.state = "active" if should_be_active else "paused" if not setting.is_enabled else "blocked"
            pair.next_scheduled_at = next_run if should_be_active else None
            if not should_be_active and pair.last_result is None:
                pair.last_result = "skipped"
                pair.last_error = "Warm-up pair is inactive because global warm-up is paused or one of the mailboxes is not eligible."
            self.db.add(pair)

        for sender_id, recipient_id in desired_pairs:
            if (sender_id, recipient_id) in existing_pairs:
                continue
            self.db.add(
                WarmupPair(
                    sender_mailbox_id=sender_id,
                    recipient_mailbox_id=recipient_id,
                    is_active=True,
                    state="active",
                    next_scheduled_at=next_run,
                )
            )

        if commit:
            self.db.commit()

    def process_all_active_pairs(self, *, force_send: bool = False) -> dict:
        setting = self.get_or_create_settings()
        if not setting.is_enabled:
            return {"processed": 0, "status": "paused"}

        self.sync_pairs()
        active_pairs = (
            self.db.query(WarmupPair)
            .options(joinedload(WarmupPair.sender), joinedload(WarmupPair.recipient))
            .filter(WarmupPair.is_active == True)
            .all()
        )

        processed = 0
        for pair in active_pairs:
            if force_send or random.random() > 0.3:
                self._attempt_send(pair)
                processed += 1
            else:
                self._record_skipped_event(pair, "Randomized warm-up skip to avoid bulk sending patterns.")
        return {"processed": processed, "status": "completed"}

    def _attempt_send(self, pair: WarmupPair) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        daily_limit = WarmupPlanner.get_daily_limit(pair.sender)
        sent_today = self._sender_success_count_today(pair.sender_mailbox_id)

        if sent_today >= daily_limit:
            self._record_skipped_event(pair, "Daily warm-up limit reached for this mailbox.")
            return

        subject = random.choice([
            "Quick question",
            "Checking in",
            "Hello there",
            "Meeting next week?",
            "Following up on our chat",
        ])
        body = random.choice([
            "Just wanted to reach out and say hi.",
            "Are you available for a quick chat?",
            "Hope you are doing well.",
            "Let me know your thoughts on this.",
        ])

        event = WarmupEvent(
            mailbox_id=pair.sender_mailbox_id,
            pair_id=pair.id,
            recipient_mailbox_id=pair.recipient_mailbox_id,
            event_type="send",
            target_email=pair.recipient.email,
            subject=subject,
            body_preview=body,
            status="queued",
            scheduled_for=pair.next_scheduled_at or WarmupPlanner.next_run_at(now),
            result_detail="Warm-up send queued for execution.",
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        req = SendEmailRequest(
            mailbox_id=pair.sender_mailbox_id,
            to=[pair.recipient.email],
            subject=subject,
            text_body=body,
        )

        try:
            self.smtp.send_email(req)
            event.status = "success"
            event.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
            event.result_detail = "Warm-up email sent successfully."
            pair.last_sent_at = event.sent_at
            pair.last_result = "success"
            pair.last_error = None
            pair.next_scheduled_at = WarmupPlanner.next_run_at()
            pair.state = "active"
            self._update_mailbox_warmup_outcome(pair.sender, "success", None)
        except SMTPServiceError as exc:
            event.status = "failed"
            event.error_category = exc.category
            event.result_detail = exc.message
            pair.last_result = "failed"
            pair.last_error = exc.message
            pair.next_scheduled_at = WarmupPlanner.next_run_at()
            pair.state = "active"
            self._update_mailbox_warmup_outcome(pair.sender, "failed", exc.message)

        self.db.add(event)
        self.db.add(pair)
        self.db.commit()

    def _record_skipped_event(self, pair: WarmupPair, detail: str) -> None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        event = WarmupEvent(
            mailbox_id=pair.sender_mailbox_id,
            pair_id=pair.id,
            recipient_mailbox_id=pair.recipient_mailbox_id,
            event_type="send",
            target_email=pair.recipient.email,
            subject=None,
            body_preview=None,
            status="skipped",
            scheduled_for=pair.next_scheduled_at or WarmupPlanner.next_run_at(now),
            result_detail=detail,
        )
        pair.last_result = "skipped"
        pair.last_error = detail
        pair.next_scheduled_at = WarmupPlanner.next_run_at(now)
        self._update_mailbox_warmup_outcome(pair.sender, "skipped", detail)
        self.db.add(event)
        self.db.add(pair)
        self.db.commit()

    def _mailbox_status_rows(self) -> list[dict]:
        rows = []
        for mailbox in self.db.query(Mailbox).order_by(Mailbox.email.asc()).all():
            rows.append(self._refresh_mailbox_warmup_state(mailbox))
        return rows

    def _refresh_mailbox_warmup_state(self, mailbox: Mailbox) -> dict:
        block_reason = None
        status = "disabled"
        if mailbox.status != "active":
            status = "blocked"
            block_reason = "Mailbox is inactive."
        else:
            try:
                self.providers.resolve_mailbox_provider(mailbox)
            except ProviderUnavailableError as exc:
                status = "blocked"
                block_reason = exc.message
            else:
                if not mailbox.warmup_enabled:
                    status = "disabled"
                elif mailbox.smtp_last_check_status != "healthy":
                    status = "blocked"
                    block_reason = mailbox.smtp_last_check_message or "SMTP check must pass before warm-up can run."
                else:
                    status = "ready"

        mailbox.warmup_status = status
        mailbox.warmup_block_reason = block_reason
        mailbox.warmup_last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if mailbox.warmup_last_result is None:
            mailbox.warmup_last_result = "never_run"
        self.db.add(mailbox)
        return {
            "mailbox_uuid": mailbox.id,
            "id": str(mailbox.id),
            "email": mailbox.email,
            "display_name": mailbox.display_name,
            "provider_type": mailbox.provider_type,
            "warmup_enabled": mailbox.warmup_enabled,
            "warmup_status": status,
            "warmup_last_checked_at": mailbox.warmup_last_checked_at.isoformat() if mailbox.warmup_last_checked_at else None,
            "warmup_last_result": mailbox.warmup_last_result,
            "warmup_block_reason": block_reason,
            "warmup_recommendation": self._mailbox_recommendation(mailbox, status, block_reason),
            "smtp_last_check_status": mailbox.smtp_last_check_status,
            "smtp_last_check_message": mailbox.smtp_last_check_message,
            "status": mailbox.status,
            "current_warmup_stage": mailbox.current_warmup_stage,
        }

    def _update_mailbox_warmup_outcome(self, mailbox: Mailbox, result: str, block_reason: str | None) -> None:
        mailbox.warmup_last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        mailbox.warmup_last_result = result
        mailbox.warmup_block_reason = block_reason
        mailbox.warmup_status = "ready" if result == "success" else mailbox.warmup_status or "blocked"
        self.db.add(mailbox)

    def _mailbox_recommendation(self, mailbox: Mailbox, status: str, block_reason: str | None) -> str:
        if mailbox.status != "active":
            return "Activate this mailbox before warm-up can use it."
        if block_reason:
            return block_reason
        if not mailbox.warmup_enabled:
            return "Enable warm-up participation for this mailbox."
        if status == "ready":
            return "Ready for warm-up pairing and worker dispatch."
        if mailbox.smtp_last_check_status != "healthy":
            return mailbox.smtp_last_check_message or "Run and pass SMTP diagnostics before warm-up can use this mailbox."
        return "Check provider and mailbox configuration before warm-up."

    def _next_action(
        self,
        global_enabled: bool,
        worker_status: dict,
        scheduler_status: dict,
        mailboxes: list[dict],
        active_pair_count: int,
    ) -> str:
        enabled_mailboxes = [mailbox for mailbox in mailboxes if mailbox["warmup_enabled"]]
        ready_mailboxes = [mailbox for mailbox in enabled_mailboxes if mailbox["warmup_status"] == "ready"]
        if not global_enabled:
            return "Start warm-up globally when you are ready to queue worker-backed warm-up passes."
        if worker_status.get("status") != "healthy":
            return worker_status.get("detail") or "Start the worker process before warm-up can run."
        if not enabled_mailboxes:
            return "Enable warm-up on at least two mailboxes."
        if len(ready_mailboxes) < 2:
            return "Fix SMTP/provider blockers until at least two warm-up-enabled mailboxes are ready."
        if active_pair_count == 0:
            return "Warm-up can create pairs on the next status refresh or run-now action."
        if scheduler_status.get("status") != "healthy":
            return "Use Run now for manual recovery, then fix scheduler/beat so automatic passes continue."
        return "Warm-up is ready. Wait for the next scheduled pass or use Run now for an internal test."

    def _scheduler_status(self) -> dict:
        if not settings.BACKGROUND_WORKERS_ENABLED:
            return {
                "status": "disabled",
                "detail": "Workers are disabled in the current runtime mode.",
                "last_seen_at": None,
            }

        latest_job = (
            self.db.query(JobLog)
            .filter(JobLog.job_type == "warmup_cycle")
            .order_by(JobLog.created_at.desc())
            .first()
        )
        if not latest_job:
            return {
                "status": "stale",
                "detail": "No warm-up scheduler activity has been recorded yet.",
                "last_seen_at": None,
            }

        last_seen = latest_job.created_at or latest_job.started_at or latest_job.finished_at
        if not last_seen:
            return {
                "status": "stale",
                "detail": "Warm-up scheduler activity has no usable timestamp.",
                "last_seen_at": None,
            }

        age = (datetime.now(timezone.utc).replace(tzinfo=None) - last_seen).total_seconds()
        if age > SCHEDULER_STALE_AFTER_SECONDS:
            return {
                "status": "stale",
                "detail": "Warm-up scheduler activity is stale. Automatic warm-up passes are not being queued on time.",
                "last_seen_at": last_seen.isoformat(),
            }

        return {
            "status": "healthy",
            "detail": "Warm-up scheduler is queuing jobs on the expected cadence.",
            "last_seen_at": last_seen.isoformat(),
        }

    def _collect_blockers(self, global_enabled: bool, worker_status: dict, scheduler_status: dict, mailboxes: list[dict]) -> list[dict]:
        blockers: list[dict] = []
        if not global_enabled:
            blockers.append({"code": "warmup_paused", "message": "Warm-up is paused globally."})
        if worker_status.get("status") != "healthy":
            blockers.append({"code": "workers_unavailable", "message": worker_status.get("detail") or "Workers are unavailable."})
        if scheduler_status.get("status") != "healthy":
            blockers.append({"code": "scheduler_unhealthy", "message": scheduler_status.get("detail") or "Scheduler is not healthy."})

        enabled_mailboxes = [mailbox for mailbox in mailboxes if mailbox["warmup_enabled"]]
        ready_mailboxes = [mailbox for mailbox in enabled_mailboxes if mailbox["warmup_status"] == "ready"]
        if not enabled_mailboxes:
            blockers.append({"code": "no_warmup_mailboxes", "message": "No mailboxes have warm-up enabled."})
        elif len(ready_mailboxes) < 2:
            blockers.append({"code": "insufficient_mailboxes", "message": "At least 2 SMTP-healthy warm-up-enabled mailboxes are required."})

        smtp_blocked = [mailbox["email"] for mailbox in enabled_mailboxes if mailbox["warmup_status"] == "blocked"]
        if smtp_blocked:
            blockers.append({"code": "smtp_unhealthy", "message": f"SMTP check failed or mailbox is inactive for: {', '.join(smtp_blocked)}"})
        return blockers

    def _compute_health_percent(self, mailboxes: list[dict], successful_sends_today: int, failed_sends_today: int) -> int | None:
        ready_mailbox_count = len([mailbox for mailbox in mailboxes if mailbox["warmup_status"] == "ready"])
        total_attempts = successful_sends_today + failed_sends_today
        if ready_mailbox_count == 0 or total_attempts == 0:
            return None
        return int((successful_sends_today / total_attempts) * 100)

    def _next_run_at(self, global_enabled: bool, worker_status: dict, scheduler_status: dict, mailboxes: list[dict]) -> str | None:
        ready_mailboxes = [mailbox for mailbox in mailboxes if mailbox["warmup_status"] == "ready"]
        if (
            not global_enabled
            or worker_status.get("status") != "healthy"
            or scheduler_status.get("status") != "healthy"
            or len(ready_mailboxes) < 2
        ):
            return None
        return WarmupPlanner.next_run_at().isoformat()

    def _today_send_counts(self) -> tuple[int, int]:
        today = datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
        success = (
            self.db.query(func.count(WarmupEvent.id))
            .filter(
                WarmupEvent.event_type == "send",
                WarmupEvent.created_at >= today,
                WarmupEvent.status == "success",
            )
            .scalar()
            or 0
        )
        failed = (
            self.db.query(func.count(WarmupEvent.id))
            .filter(
                WarmupEvent.event_type == "send",
                WarmupEvent.created_at >= today,
                WarmupEvent.status == "failed",
            )
            .scalar()
            or 0
        )
        return success, failed

    def _sender_success_count_today(self, sender_mailbox_id) -> int:
        today = datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(func.count(WarmupEvent.id))
            .filter(
                WarmupEvent.mailbox_id == sender_mailbox_id,
                WarmupEvent.event_type == "send",
                WarmupEvent.created_at >= today,
                WarmupEvent.status == "success",
            )
            .scalar()
            or 0
        )

    def _pair_daily_sent_count(self, sender_mailbox_id, recipient_mailbox_id) -> int:
        today = datetime.now(timezone.utc).replace(tzinfo=None).replace(hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(func.count(WarmupEvent.id))
            .filter(
                WarmupEvent.mailbox_id == sender_mailbox_id,
                WarmupEvent.recipient_mailbox_id == recipient_mailbox_id,
                WarmupEvent.event_type == "send",
                WarmupEvent.created_at >= today,
                WarmupEvent.status == "success",
            )
            .scalar()
            or 0
        )
