from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    is_read: int
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedNotifications(BaseModel):
    total_count: int
    unread_count: int
    items: List[NotificationResponse]


class NotificationMarkRead(BaseModel):
    notification_ids: List[int]
