from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.notifications import NotificationSummary
from app.services.notification_service import NotificationService


router = APIRouter()


@router.get("/summary", response_model=NotificationSummary)
def notification_summary(
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return NotificationService(db).summary(user=current_user, limit=limit)


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return NotificationService(db).mark_read(user=current_user, notification_key=notification_id)


@router.post("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return NotificationService(db).mark_all_read(user=current_user)

