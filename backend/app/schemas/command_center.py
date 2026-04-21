from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, UUID4, Field


TASK_STATUSES = {"todo", "in_progress", "blocked", "done", "dismissed"}
TASK_PRIORITIES = {"critical", "high", "normal", "low"}
TASK_CATEGORIES = {"campaign", "inbox", "deliverability", "warmup", "provider", "domain", "mailbox", "system", "manual"}
ACTION_RESULTS = {"success", "failed", "blocked", "skipped", "info"}


class OperatorTaskCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    status: str = "todo"
    priority: str = "normal"
    category: str = "manual"
    due_at: datetime | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID4 | None = None
    metadata: dict[str, Any] | None = None


class OperatorTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    due_at: datetime | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID4 | None = None
    metadata: dict[str, Any] | None = None


class OperatorTaskResponse(BaseModel):
    id: UUID4
    title: str
    description: str | None = None
    status: str
    priority: str
    category: str
    due_at: datetime | None = None
    related_entity_type: str | None = None
    related_entity_id: UUID4 | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class OperatorActionLogResponse(BaseModel):
    id: UUID4
    action_type: str
    source: str
    result: str
    message: str
    related_entity_type: str | None = None
    related_entity_id: UUID4 | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime


class DailyNoteUpsert(BaseModel):
    note_date: date
    content: str = ""


class DailyNoteResponse(BaseModel):
    id: UUID4
    note_date: date
    content: str
    created_at: datetime
    updated_at: datetime


class RunbookStepPayload(BaseModel):
    step_order: int = 1
    title: str = Field(min_length=1)
    description: str | None = None
    default_status: str = "todo"


class RunbookCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    category: str = "manual"
    is_active: bool = True
    steps: list[RunbookStepPayload] = []


class RunbookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    is_active: bool | None = None
    steps: list[RunbookStepPayload] | None = None


class RunbookStepResponse(BaseModel):
    id: UUID4
    runbook_id: UUID4
    step_order: int
    title: str
    description: str | None = None
    default_status: str
    created_at: datetime
    updated_at: datetime


class RunbookResponse(BaseModel):
    id: UUID4
    name: str
    description: str | None = None
    category: str
    is_active: bool
    steps: list[RunbookStepResponse]
    created_at: datetime
    updated_at: datetime


class CommandCenterSummary(BaseModel):
    today_tasks: list[OperatorTaskResponse]
    overdue_tasks: list[OperatorTaskResponse]
    blocked_tasks: list[OperatorTaskResponse]
    recent_actions: list[OperatorActionLogResponse]
    stats: dict[str, int]
