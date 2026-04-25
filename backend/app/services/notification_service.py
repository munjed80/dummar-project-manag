"""
Notification service — creates in-app notifications for important events.
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
    from app.services.execution_log import (
        ACTION_TYPE_NOTIFICATION,
        track_execution,
    )

    with track_execution(
        ACTION_TYPE_NOTIFICATION,
        "create_notification",
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        payload={
            "notification_type": getattr(notification_type, "value", str(notification_type)),
            "title": title,
        },
    ):
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


# ─────────────────────────────────────────────────────────────
# Contract Intelligence Notifications
# ─────────────────────────────────────────────────────────────

def notify_intelligence_processing_complete(
    db: Session,
    event: str,
    document_id: Optional[int] = None,
    batch_id: Optional[str] = None,
    details: Optional[str] = None,
):
    """
    Send notification when contract intelligence processing completes.

    Events:
    - ocr_complete: OCR processing finished
    - extraction_review_ready: extraction done, review needed
    - duplicate_review_needed: duplicates found needing attention
    - risk_review_needed: high/critical risk flags detected
    - batch_import_complete: bulk import finished
    - batch_import_failed: bulk import had significant failures

    Only notifies contracts_manager and project_director.
    Failures in notification never break the calling workflow.
    """
    try:
        event_labels = {
            "ocr_complete": "اكتملت معالجة OCR",
            "extraction_review_ready": "بيانات مستخرجة جاهزة للمراجعة",
            "duplicate_review_needed": "تكرارات محتملة تحتاج مراجعة",
            "risk_review_needed": "مخاطر مرتفعة تحتاج انتباه",
            "batch_import_complete": "اكتمل الاستيراد الجماعي",
            "batch_import_failed": "فشل كبير في الاستيراد الجماعي",
        }

        title = event_labels.get(event, "تحديث ذكاء العقود")
        message = title
        if details:
            message = f"{title}: {details}"
        if document_id:
            message += f" (مستند #{document_id})"
        if batch_id:
            message += f" (دفعة {batch_id})"

        # Notify contracts managers and project director
        managers = db.query(User.id).filter(
            User.role.in_([UserRole.CONTRACTS_MANAGER, UserRole.PROJECT_DIRECTOR]),
            User.is_active == 1,
        ).all()

        for (uid,) in managers:
            create_notification(
                db=db,
                user_id=uid,
                notification_type=NotificationType.INTELLIGENCE_PROCESSING,
                title=title,
                message=message,
                entity_type="contract_document" if document_id else "batch_import",
                entity_id=document_id,
            )

        logger.info(
            "Sent %d intelligence notifications: event=%s, doc=%s, batch=%s",
            len(managers), event, document_id, batch_id,
        )
    except Exception:
        logger.exception("Failed to send intelligence notification (event=%s)", event)


# ─────────────────────────────────────────────────────────────
# Location Notifications
# ─────────────────────────────────────────────────────────────

def notify_location_event(
    db: Session,
    event: str,
    location_id: int,
    location_name: str,
    details: Optional[str] = None,
):
    """
    Send notification for location-related events.

    Events:
    - hotspot_detected: location became a hotspot (≥5 open complaints)
    - location_created: new location created
    - location_updated: location data changed
    - location_contract_linked: contract linked to location
    - location_contract_unlinked: contract unlinked from location

    Notifies project_director, area_supervisor, and engineer_supervisor.
    Failures never break the calling workflow.
    """
    try:
        event_labels = {
            "hotspot_detected": "تم اكتشاف نقطة ساخنة",
            "location_created": "تم إنشاء موقع جديد",
            "location_updated": "تم تحديث بيانات موقع",
            "location_contract_linked": "تم ربط عقد بموقع",
            "location_contract_unlinked": "تم فك ربط عقد من موقع",
        }

        title = event_labels.get(event, "تحديث الموقع")
        message = f"{title}: {location_name}"
        if details:
            message = f"{message} — {details}"

        # Notify relevant roles
        managers = db.query(User.id).filter(
            User.role.in_([
                UserRole.PROJECT_DIRECTOR,
                UserRole.AREA_SUPERVISOR,
                UserRole.ENGINEER_SUPERVISOR,
            ]),
            User.is_active == 1,
        ).all()

        for (uid,) in managers:
            create_notification(
                db=db,
                user_id=uid,
                notification_type=NotificationType.LOCATION_ALERT,
                title=title,
                message=message,
                entity_type="location",
                entity_id=location_id,
            )

        logger.info(
            "Sent %d location notifications: event=%s, location_id=%d",
            len(managers), event, location_id,
        )
    except Exception:
        logger.exception("Failed to send location notification (event=%s)", event)
