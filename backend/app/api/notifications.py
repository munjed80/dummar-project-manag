from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    PaginatedNotifications,
    NotificationMarkRead,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=PaginatedNotifications)
def list_notifications(
    skip: int = 0,
    limit: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notifications for the current user."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read == 0)
        .count()
    )

    if unread_only:
        query = query.filter(Notification.is_read == 0)

    total_count = query.count()
    items = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()

    return {
        "total_count": total_count,
        "unread_count": unread_count,
        "items": items,
    }


@router.post("/mark-read")
def mark_notifications_read(
    data: NotificationMarkRead,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark specific notifications as read."""
    updated = (
        db.query(Notification)
        .filter(
            Notification.id.in_(data.notification_ids),
            Notification.user_id == current_user.id,
        )
        .update({Notification.is_read: 1}, synchronize_session=False)
    )
    db.commit()
    return {"marked_read": updated}


@router.post("/mark-all-read")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == 0,
        )
        .update({Notification.is_read: 1}, synchronize_session=False)
    )
    db.commit()
    return {"marked_read": updated}
