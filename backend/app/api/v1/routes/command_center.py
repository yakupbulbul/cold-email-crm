from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.command_center import DailyNote, OperatorActionLog, OperatorTask, Runbook
from app.models.user import User
from app.schemas.command_center import (
    CommandCenterSummary,
    DailyNoteResponse,
    DailyNoteUpsert,
    OperatorActionLogResponse,
    OperatorTaskCreate,
    OperatorTaskResponse,
    OperatorTaskUpdate,
    RunbookCreate,
    RunbookResponse,
    RunbookUpdate,
)
from app.services.command_center_service import ACTIVE_TASK_STATUSES, CommandCenterService

router = APIRouter()


@router.get("/summary", response_model=CommandCenterSummary)
def get_command_center_summary(db: Session = Depends(get_db)):
    return CommandCenterService(db).summary()


@router.get("/tasks", response_model=list[OperatorTaskResponse])
def list_tasks(
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    active_only: bool = False,
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
):
    query = db.query(OperatorTask)
    if active_only:
        query = query.filter(OperatorTask.status.in_(ACTIVE_TASK_STATUSES))
    if status:
        query = query.filter(OperatorTask.status == status)
    if category:
        query = query.filter(OperatorTask.category == category)
    if priority:
        query = query.filter(OperatorTask.priority == priority)
    tasks = query.order_by(OperatorTask.updated_at.desc()).limit(limit).all()
    service = CommandCenterService(db)
    return [service.serialize_task(task) for task in tasks]


@router.post("/tasks", response_model=OperatorTaskResponse)
def create_task(
    payload: OperatorTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = CommandCenterService(db).create_task(actor=current_user, payload=payload)
    return CommandCenterService(db).serialize_task(task)


@router.patch("/tasks/{task_id}", response_model=OperatorTaskResponse)
def update_task(task_id: UUID, payload: OperatorTaskUpdate, db: Session = Depends(get_db)):
    service = CommandCenterService(db)
    task = service.update_task(task_id, payload)
    return service.serialize_task(task)


@router.get("/actions", response_model=list[OperatorActionLogResponse])
def list_actions(
    source: str | None = None,
    result: str | None = None,
    action_type: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    db: Session = Depends(get_db),
):
    query = db.query(OperatorActionLog)
    if source:
        query = query.filter(OperatorActionLog.source == source)
    if result:
        query = query.filter(OperatorActionLog.result == result)
    if action_type:
        query = query.filter(OperatorActionLog.action_type == action_type)
    if related_entity_type:
        query = query.filter(OperatorActionLog.related_entity_type == related_entity_type)
    if related_entity_id:
        query = query.filter(OperatorActionLog.related_entity_id == related_entity_id)
    actions = query.order_by(OperatorActionLog.created_at.desc()).limit(limit).all()
    service = CommandCenterService(db)
    return [service.serialize_action(action) for action in actions]


@router.get("/daily-notes", response_model=list[DailyNoteResponse])
def list_daily_notes(limit: int = Query(default=30, ge=1, le=120), db: Session = Depends(get_db)):
    notes = db.query(DailyNote).order_by(DailyNote.note_date.desc()).limit(limit).all()
    service = CommandCenterService(db)
    return [service.serialize_note(note) for note in notes]


@router.get("/daily-notes/{note_date}", response_model=DailyNoteResponse | None)
def get_daily_note(note_date: date, db: Session = Depends(get_db)):
    note = db.query(DailyNote).filter(DailyNote.note_date == note_date).first()
    return CommandCenterService(db).serialize_note(note) if note else None


@router.post("/daily-notes", response_model=DailyNoteResponse)
def upsert_daily_note(
    payload: DailyNoteUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = CommandCenterService(db)
    note = service.upsert_daily_note(actor=current_user, note_date=payload.note_date, content=payload.content)
    return service.serialize_note(note)


@router.patch("/daily-notes/{note_date}", response_model=DailyNoteResponse)
def patch_daily_note(
    note_date: date,
    payload: DailyNoteUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = CommandCenterService(db)
    note = service.upsert_daily_note(actor=current_user, note_date=note_date, content=payload.content)
    return service.serialize_note(note)


@router.get("/runbooks", response_model=list[RunbookResponse])
def list_runbooks(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Runbook).options(joinedload(Runbook.steps))
    if active_only:
        query = query.filter(Runbook.is_active.is_(True))
    runbooks = query.order_by(Runbook.category.asc(), Runbook.name.asc()).all()
    service = CommandCenterService(db)
    return [service.serialize_runbook(runbook) for runbook in runbooks]


@router.post("/runbooks", response_model=RunbookResponse)
def create_runbook(
    payload: RunbookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = CommandCenterService(db)
    runbook = service.create_runbook(actor=current_user, payload=payload)
    return service.serialize_runbook(runbook)


@router.patch("/runbooks/{runbook_id}", response_model=RunbookResponse)
def update_runbook(runbook_id: UUID, payload: RunbookUpdate, db: Session = Depends(get_db)):
    service = CommandCenterService(db)
    runbook = service.update_runbook(runbook_id, payload)
    return service.serialize_runbook(runbook)


@router.post("/runbooks/{runbook_id}/start", response_model=list[OperatorTaskResponse])
def start_runbook(
    runbook_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = CommandCenterService(db)
    tasks = service.start_runbook(runbook_id, actor=current_user)
    return [service.serialize_task(task) for task in tasks]
