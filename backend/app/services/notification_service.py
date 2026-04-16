"""
Notification service — creates in-app notifications for important events.

Future expansion: add email sending, push notifications, etc.
"""
import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user_id: int,
    notification_type: NotificationType,
    title: str,
    message: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> Notification:
    """Create a single in-app notification for a user."""
    notif = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def notify_complaint_status_change(
    db: Session,
    complaint_id: int,
    tracking_number: str,
    old_status: str,
    new_status: str,
    assigned_to_id: Optional[int] = None,
):
    """
    Send notification when complaint status changes.
    Notifies:
    - The assigned officer (if any)
    - All complaints officers and project director
    """
    status_labels = {
        "new": "جديدة",
        "under_review": "قيد المراجعة",
        "assigned": "تم التعيين",
        "in_progress": "قيد التنفيذ",
        "resolved": "تم الحل",
        "rejected": "مرفوضة",
    }
    old_label = status_labels.get(old_status, old_status)
    new_label = status_labels.get(new_status, new_status)

    title = f"تحديث حالة الشكوى {tracking_number}"
    message = f"تم تغيير حالة الشكوى {tracking_number} من '{old_label}' إلى '{new_label}'"

    # Collect unique user IDs to notify
    notify_user_ids: set[int] = set()

    if assigned_to_id:
        notify_user_ids.add(assigned_to_id)

    # Notify complaints officers and project director
    officers = db.query(User.id).filter(
        User.role.in_([UserRole.COMPLAINTS_OFFICER, UserRole.PROJECT_DIRECTOR]),
        User.is_active == 1,
    ).all()
    for (uid,) in officers:
        notify_user_ids.add(uid)

    for uid in notify_user_ids:
        create_notification(
            db=db,
            user_id=uid,
            notification_type=NotificationType.COMPLAINT_STATUS,
            title=title,
            message=message,
            entity_type="complaint",
            entity_id=complaint_id,
        )

    logger.info(
        "Sent %d notifications for complaint %s status change",
        len(notify_user_ids),
        tracking_number,
    )


def notify_task_assigned(
    db: Session,
    task_id: int,
    task_title: str,
    assigned_to_id: int,
):
    """Send notification when a task is assigned to a user."""
    create_notification(
        db=db,
        user_id=assigned_to_id,
        notification_type=NotificationType.TASK_ASSIGNED,
        title="مهمة جديدة مُسندة إليك",
        message=f"تم إسناد المهمة '{task_title}' إليك",
        entity_type="task",
        entity_id=task_id,
    )


def notify_contract_status_change(
    db: Session,
    contract_id: int,
    contract_number: str,
    action: str,
):
    """
    Send notification when contract status changes (approved, activated, etc.).
    Notifies contracts managers and project director.
    """
    action_labels = {
        "approve": "تمت الموافقة",
        "activate": "تم التفعيل",
        "complete": "تم الإنجاز",
        "suspend": "تم التعليق",
        "cancel": "تم الإلغاء",
    }
    action_label = action_labels.get(action, action)

    title = f"تحديث العقد {contract_number}"
    message = f"العقد {contract_number}: {action_label}"

    # Notify contracts managers and project director
    managers = db.query(User.id).filter(
        User.role.in_([UserRole.CONTRACTS_MANAGER, UserRole.PROJECT_DIRECTOR]),
        User.is_active == 1,
    ).all()

    for (uid,) in managers:
        create_notification(
            db=db,
            user_id=uid,
            notification_type=NotificationType.CONTRACT_UPDATED,
            title=title,
            message=message,
            entity_type="contract",
            entity_id=contract_id,
        )

    logger.info(
        "Sent %d notifications for contract %s action=%s",
        len(managers),
        contract_number,
        action,
    )
