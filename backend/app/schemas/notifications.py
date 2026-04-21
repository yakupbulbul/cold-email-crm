from datetime import datetime

from pydantic import BaseModel


class HeaderNotification(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    source: str
    status: str
    created_at: datetime
    href: str | None = None
    read_at: datetime | None = None


class NotificationSummary(BaseModel):
    unread_count: int
    items: list[HeaderNotification]

