from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.command_center import DailyNote, OperatorActionLog, OperatorTask, Runbook, RunbookStep
from app.models.user import User
from app.schemas.command_center import ACTION_RESULTS, TASK_CATEGORIES, TASK_PRIORITIES, TASK_STATUSES


ACTIVE_TASK_STATUSES = {"todo", "in_progress", "blocked"}
TERMINAL_TASK_STATUSES = {"done", "dismissed"}


def _validate_choice(value: str, allowed: set[str], field_name: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in allowed:
        raise HTTPException(status_code=422, detail=f"{field_name} must be one of: {', '.join(sorted(allowed))}.")
    return normalized


def _safe_metadata(metadata: dict | None) -> dict | None:
    if not metadata:
        return None
    blocked_keys = {"password", "token", "secret", "refresh_token", "access_token", "smtp_password", "imap_password"}
    return {
        key: value
        for key, value in metadata.items()
        if key.lower() not in blocked_keys
    }


class CommandCenterService:
    def __init__(self, db: Session):
        self.db = db

    def serialize_task(self, task: OperatorTask) -> dict:
        return {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "category": task.category,
            "due_at": task.due_at.isoformat() if task.due_at else None,
            "related_entity_type": task.related_entity_type,
            "related_entity_id": str(task.related_entity_id) if task.related_entity_id else None,
            "metadata": task.metadata_blob or {},
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }

    def serialize_action(self, action: OperatorActionLog) -> dict:
        return {
            "id": str(action.id),
            "action_type": action.action_type,
            "source": action.source,
            "result": action.result,
            "message": action.message,
            "related_entity_type": action.related_entity_type,
            "related_entity_id": str(action.related_entity_id) if action.related_entity_id else None,
            "metadata": action.metadata_blob or {},
            "created_at": action.created_at.isoformat() if action.created_at else None,
        }

    def serialize_note(self, note: DailyNote) -> dict:
        return {
            "id": str(note.id),
            "note_date": note.note_date.isoformat(),
            "content": note.content,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }

    def serialize_runbook(self, runbook: Runbook) -> dict:
        return {
            "id": str(runbook.id),
            "name": runbook.name,
            "description": runbook.description,
            "category": runbook.category,
            "is_active": runbook.is_active,
            "steps": [
                {
                    "id": str(step.id),
                    "runbook_id": str(step.runbook_id),
                    "step_order": step.step_order,
                    "title": step.title,
                    "description": step.description,
                    "default_status": step.default_status,
                    "created_at": step.created_at.isoformat() if step.created_at else None,
                    "updated_at": step.updated_at.isoformat() if step.updated_at else None,
                }
                for step in sorted(runbook.steps or [], key=lambda item: item.step_order)
            ],
            "created_at": runbook.created_at.isoformat() if runbook.created_at else None,
            "updated_at": runbook.updated_at.isoformat() if runbook.updated_at else None,
        }

    def create_task(self, *, actor: User | None, payload) -> OperatorTask:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Task title is required.")
        task = OperatorTask(
            title=title,
            description=payload.description,
            status=_validate_choice(payload.status, TASK_STATUSES, "status"),
            priority=_validate_choice(payload.priority, TASK_PRIORITIES, "priority"),
            category=_validate_choice(payload.category, TASK_CATEGORIES, "category"),
            due_at=payload.due_at,
            related_entity_type=payload.related_entity_type,
            related_entity_id=payload.related_entity_id,
            metadata_blob=_safe_metadata(payload.metadata),
            created_by_user_id=actor.id if actor else None,
        )
        self.db.add(task)
        self.record_action(
            action_type="task_created",
            source="command_center",
            result="success",
            message=f"Task created: {title}",
            related_entity_type=payload.related_entity_type,
            related_entity_id=payload.related_entity_id,
            actor=actor,
            metadata={"task_id": str(task.id), "category": task.category, "priority": task.priority},
            commit=False,
        )
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_task(self, task_id: UUID, payload) -> OperatorTask:
        task = self.db.query(OperatorTask).filter(OperatorTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if payload.title is not None:
            title = payload.title.strip()
            if not title:
                raise HTTPException(status_code=422, detail="Task title is required.")
            task.title = title
        if payload.description is not None:
            task.description = payload.description
        if payload.status is not None:
            task.status = _validate_choice(payload.status, TASK_STATUSES, "status")
        if payload.priority is not None:
            task.priority = _validate_choice(payload.priority, TASK_PRIORITIES, "priority")
        if payload.category is not None:
            task.category = _validate_choice(payload.category, TASK_CATEGORIES, "category")
        if "due_at" in payload.model_fields_set:
            task.due_at = payload.due_at
        if "related_entity_type" in payload.model_fields_set:
            task.related_entity_type = payload.related_entity_type
        if "related_entity_id" in payload.model_fields_set:
            task.related_entity_id = payload.related_entity_id
        if payload.metadata is not None:
            task.metadata_blob = _safe_metadata(payload.metadata)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def upsert_daily_note(self, *, actor: User | None, note_date: date, content: str) -> DailyNote:
        note = self.db.query(DailyNote).filter(DailyNote.note_date == note_date).first()
        if note:
            note.content = content
            self.db.add(note)
        else:
            note = DailyNote(note_date=note_date, content=content, created_by_user_id=actor.id if actor else None)
            self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def create_runbook(self, *, actor: User | None, payload) -> Runbook:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Runbook name is required.")
        runbook = Runbook(
            name=name,
            description=payload.description,
            category=_validate_choice(payload.category, TASK_CATEGORIES, "category"),
            is_active=payload.is_active,
            created_by_user_id=actor.id if actor else None,
        )
        self.db.add(runbook)
        self.db.flush()
        self._replace_runbook_steps(runbook, payload.steps or [])
        self.db.commit()
        return self.db.query(Runbook).options(joinedload(Runbook.steps)).filter(Runbook.id == runbook.id).one()

    def update_runbook(self, runbook_id: UUID, payload) -> Runbook:
        runbook = self.db.query(Runbook).options(joinedload(Runbook.steps)).filter(Runbook.id == runbook_id).first()
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        if payload.name is not None:
            name = payload.name.strip()
            if not name:
                raise HTTPException(status_code=422, detail="Runbook name is required.")
            runbook.name = name
        if payload.description is not None:
            runbook.description = payload.description
        if payload.category is not None:
            runbook.category = _validate_choice(payload.category, TASK_CATEGORIES, "category")
        if payload.is_active is not None:
            runbook.is_active = payload.is_active
        if payload.steps is not None:
            self._replace_runbook_steps(runbook, payload.steps)
        self.db.add(runbook)
        self.db.commit()
        return self.db.query(Runbook).options(joinedload(Runbook.steps)).filter(Runbook.id == runbook.id).one()

    def _replace_runbook_steps(self, runbook: Runbook, steps: list) -> None:
        self.db.query(RunbookStep).filter(RunbookStep.runbook_id == runbook.id).delete(synchronize_session=False)
        for index, step_payload in enumerate(sorted(steps, key=lambda item: item.step_order), start=1):
            title = step_payload.title.strip()
            if not title:
                raise HTTPException(status_code=422, detail="Runbook step title is required.")
            self.db.add(
                RunbookStep(
                    runbook_id=runbook.id,
                    step_order=step_payload.step_order or index,
                    title=title,
                    description=step_payload.description,
                    default_status=_validate_choice(step_payload.default_status, TASK_STATUSES, "default_status"),
                )
            )

    def start_runbook(self, runbook_id: UUID, *, actor: User | None) -> list[OperatorTask]:
        runbook = self.db.query(Runbook).options(joinedload(Runbook.steps)).filter(Runbook.id == runbook_id).first()
        if not runbook:
            raise HTTPException(status_code=404, detail="Runbook not found")
        if not runbook.is_active:
            raise HTTPException(status_code=409, detail="Inactive runbooks cannot be started.")
        steps = sorted(runbook.steps or [], key=lambda item: item.step_order)
        if not steps:
            steps = [RunbookStep(runbook_id=runbook.id, step_order=1, title=runbook.name, description=runbook.description, default_status="todo")]
        tasks = []
        for step in steps:
            task = OperatorTask(
                title=step.title,
                description=step.description,
                status=step.default_status if step.default_status in TASK_STATUSES else "todo",
                priority="normal",
                category=runbook.category,
                metadata_blob={"runbook_id": str(runbook.id), "runbook_name": runbook.name, "step_order": step.step_order},
                created_by_user_id=actor.id if actor else None,
            )
            self.db.add(task)
            tasks.append(task)
        self.record_action(
            action_type="runbook_started",
            source="command_center",
            result="success",
            message=f"Runbook started: {runbook.name}",
            related_entity_type="runbook",
            related_entity_id=runbook.id,
            actor=actor,
            metadata={"tasks_created": len(tasks)},
            commit=False,
        )
        self.db.commit()
        for task in tasks:
            self.db.refresh(task)
        return tasks

    def record_action(
        self,
        *,
        action_type: str,
        source: str,
        result: str,
        message: str,
        related_entity_type: str | None = None,
        related_entity_id: UUID | str | None = None,
        actor: User | None = None,
        metadata: dict | None = None,
        commit: bool = True,
    ) -> OperatorActionLog:
        related_uuid = UUID(str(related_entity_id)) if related_entity_id else None
        action = OperatorActionLog(
            action_type=action_type,
            source=source,
            result=_validate_choice(result, ACTION_RESULTS, "result"),
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_uuid,
            actor_user_id=actor.id if actor else None,
            metadata_blob=_safe_metadata(metadata),
        )
        self.db.add(action)
        if commit:
            self.db.commit()
            self.db.refresh(action)
        return action

    def summary(self) -> dict:
        today = date.today()
        start_of_today = datetime.combine(today, time.min)
        end_of_today = datetime.combine(today, time.max)
        active_filter = OperatorTask.status.in_(ACTIVE_TASK_STATUSES)
        today_tasks = (
            self.db.query(OperatorTask)
            .filter(active_filter, OperatorTask.due_at >= start_of_today, OperatorTask.due_at <= end_of_today)
            .order_by(OperatorTask.priority.asc(), OperatorTask.due_at.asc())
            .limit(20)
            .all()
        )
        overdue_tasks = (
            self.db.query(OperatorTask)
            .filter(active_filter, OperatorTask.due_at.isnot(None), OperatorTask.due_at < start_of_today)
            .order_by(OperatorTask.due_at.asc())
            .limit(20)
            .all()
        )
        blocked_tasks = (
            self.db.query(OperatorTask)
            .filter(OperatorTask.status == "blocked")
            .order_by(OperatorTask.updated_at.desc())
            .limit(20)
            .all()
        )
        recent_actions = (
            self.db.query(OperatorActionLog)
            .order_by(OperatorActionLog.created_at.desc())
            .limit(20)
            .all()
        )
        stats = {
            "todo": self.db.query(OperatorTask).filter(OperatorTask.status == "todo").count(),
            "in_progress": self.db.query(OperatorTask).filter(OperatorTask.status == "in_progress").count(),
            "blocked": self.db.query(OperatorTask).filter(OperatorTask.status == "blocked").count(),
            "done_today": self.db.query(OperatorTask).filter(OperatorTask.status == "done", OperatorTask.updated_at >= start_of_today).count(),
            "actions_today": self.db.query(OperatorActionLog).filter(OperatorActionLog.created_at >= start_of_today).count(),
        }
        return {
            "today_tasks": [self.serialize_task(task) for task in today_tasks],
            "overdue_tasks": [self.serialize_task(task) for task in overdue_tasks],
            "blocked_tasks": [self.serialize_task(task) for task in blocked_tasks],
            "recent_actions": [self.serialize_action(action) for action in recent_actions],
            "stats": stats,
        }


def record_command_action(
    db: Session,
    *,
    action_type: str,
    source: str,
    result: str,
    message: str,
    related_entity_type: str | None = None,
    related_entity_id: UUID | str | None = None,
    actor: User | None = None,
    metadata: dict | None = None,
) -> None:
    """Best-effort operational logging that must never break the primary action."""
    try:
        CommandCenterService(db).record_action(
            action_type=action_type,
            source=source,
            result=result,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            actor=actor,
            metadata=metadata,
            commit=True,
        )
    except Exception:
        db.rollback()
