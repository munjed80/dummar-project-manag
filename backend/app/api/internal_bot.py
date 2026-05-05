import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_internal_user
from app.core import permissions as perms
from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.contract import Contract
from app.models.internal_message import Message, MessageThread
from app.models.location import Area, Location
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.internal_bot import (
    SUPPORTED_CONTEXT_TYPES,
    BotIntent,
    InternalBotQuery,
    InternalBotResponse,
    RelatedItem,
    RiskLevel,
)
from app.services.audit import write_audit_log

router = APIRouter(prefix="/internal-bot", tags=["internal-bot"])


# Statuses that indicate a complaint is still open (not terminal).
_OPEN_COMPLAINT_STATUSES = {
    ComplaintStatus.NEW,
    ComplaintStatus.UNDER_REVIEW,
    ComplaintStatus.ASSIGNED,
    ComplaintStatus.IN_PROGRESS,
}

# Maximum characters of a message body shown in the contextual analysis
# preview. Long enough to capture intent, short enough to keep the JSON
# response compact and the frontend chip readable on small screens.
_MESSAGE_PREVIEW_MAX_LENGTH = 140


def _arabic_status(status: ComplaintStatus | None) -> str:
    return {
        ComplaintStatus.NEW: "قيد المعالجة",
        ComplaintStatus.UNDER_REVIEW: "قيد المعالجة",
        ComplaintStatus.ASSIGNED: "قيد المعالجة",
        ComplaintStatus.IN_PROGRESS: "قيد التنفيذ",
        ComplaintStatus.RESOLVED: "تم الحل",
        ComplaintStatus.REJECTED: "مرفوضة",
    }.get(status, "غير محددة") if status else "غير محددة"


def _arabic_priority(priority: ComplaintPriority | None) -> str:
    return {
        ComplaintPriority.LOW: "منخفضة",
        ComplaintPriority.MEDIUM: "متوسطة",
        ComplaintPriority.HIGH: "عالية",
        ComplaintPriority.URGENT: "عاجلة",
    }.get(priority, "غير محددة") if priority else "غير محددة"


def _format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _build_complaint_analysis(db: Session, complaint: Complaint) -> InternalBotResponse:
    """Rule-based decision-support analysis for a single complaint.

    Pure deterministic logic — no external AI calls. Aggregates complaint
    metadata, the latest related task, and the linked internal-discussion
    thread, then applies simple rules to derive a risk level and a list of
    recommended next actions.
    """
    now = datetime.now(timezone.utc)
    created_at = complaint.created_at
    if created_at is not None and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_days = (now - created_at).days if created_at else 0
    is_open = complaint.status in _OPEN_COMPLAINT_STATUSES

    # Latest task linked to this complaint (if any).
    related_task = (
        db.query(Task)
        .filter(Task.complaint_id == complaint.id)
        .order_by(desc(Task.created_at), desc(Task.id))
        .first()
    )

    # Internal discussion thread linked to this complaint (Phase 2).
    thread = (
        db.query(MessageThread)
        .filter(
            MessageThread.context_type == "complaint",
            MessageThread.context_id == complaint.id,
        )
        .order_by(MessageThread.id.asc())
        .first()
    )

    message_count = 0
    last_message_at: datetime | None = None
    last_messages: list[dict[str, Any]] = []
    if thread is not None:
        message_count = (
            db.query(func.count(Message.id))
            .filter(Message.thread_id == thread.id)
            .scalar()
            or 0
        )
        recent = (
            db.query(Message)
            .filter(Message.thread_id == thread.id)
            .order_by(desc(Message.created_at), desc(Message.id))
            .limit(3)
            .all()
        )
        if recent:
            last_message_at = recent[0].created_at
            # Show in chronological order, body trimmed to ~140 chars.
            for m in reversed(recent):
                body = (m.body or "").strip()
                if len(body) > _MESSAGE_PREVIEW_MAX_LENGTH:
                    body = body[: _MESSAGE_PREVIEW_MAX_LENGTH - 3].rstrip() + "…"
                last_messages.append(
                    {
                        "sender_user_id": m.sender_user_id,
                        "created_at": _format_dt(m.created_at),
                        "body": body,
                    }
                )

    # Resolve location/area names if available.
    location_name: str | None = None
    if complaint.location_id:
        loc = db.query(Location).filter(Location.id == complaint.location_id).first()
        if loc is not None:
            location_name = loc.name
    area_name: str | None = None
    if complaint.area_id:
        area = db.query(Area).filter(Area.id == complaint.area_id).first()
        if area is not None:
            area_name = area.name_ar or area.name

    # ── Rule-based risk scoring ────────────────────────────────────────
    risk_level: RiskLevel = "low"
    if complaint.priority == ComplaintPriority.URGENT and is_open:
        risk_level = "high"
    elif complaint.priority == ComplaintPriority.HIGH and is_open and age_days >= 2:
        risk_level = "high"
    elif is_open and age_days >= 14:
        risk_level = "high"
    elif complaint.priority in (ComplaintPriority.HIGH, ComplaintPriority.URGENT) and is_open:
        risk_level = "medium"
    elif is_open and age_days >= 7:
        risk_level = "medium"
    elif is_open and complaint.status == ComplaintStatus.NEW and age_days >= 3:
        risk_level = "medium"

    # ── Key points (factual bullets) ──────────────────────────────────
    key_points: list[str] = []
    key_points.append(f"الحالة الحالية: {_arabic_status(complaint.status)}")
    key_points.append(f"الأولوية: {_arabic_priority(complaint.priority)}")
    type_label = _arabic_type(complaint.complaint_type)
    key_points.append(f"نوع الشكوى: {type_label}")
    if complaint.tracking_number:
        key_points.append(f"رقم التتبع: {complaint.tracking_number}")
    if created_at:
        if age_days == 0:
            key_points.append("عمر الشكوى: أقل من يوم واحد (جديدة)")
        elif age_days == 1:
            key_points.append("عمر الشكوى: يوم واحد")
        elif age_days == 2:
            key_points.append("عمر الشكوى: يومان")
        elif age_days <= 10:
            key_points.append(f"عمر الشكوى: {age_days} أيام")
        else:
            key_points.append(f"عمر الشكوى: {age_days} يوماً")
    if area_name:
        key_points.append(f"المنطقة: {area_name}")
    if location_name:
        key_points.append(f"الموقع: {location_name}")
    if related_task is not None:
        task_status_ar = _arabic_task_status(related_task.status)
        key_points.append(
            f"مهمة مرتبطة: «{related_task.title}» — الحالة: {task_status_ar}"
        )
    else:
        key_points.append("لا توجد مهمة تنفيذية مرتبطة حتى الآن")
    if message_count > 0:
        key_points.append(f"رسائل النقاش الداخلي: {message_count} رسالة")
    else:
        key_points.append("لم يُفتح نقاش داخلي لهذه الشكوى بعد")

    # ── Recommended actions ───────────────────────────────────────────
    recommended_actions: list[str] = []
    if not is_open:
        if complaint.status == ComplaintStatus.RESOLVED:
            recommended_actions.append("تحقق من توثيق نتيجة الإصلاح بالصور والتقرير النهائي.")
            recommended_actions.append("أغلق المهمة المرتبطة إن كانت لا تزال مفتوحة.")
            if message_count > 0:
                recommended_actions.append("راجع النقاش الداخلي وأرشفه ضمن سجل الشكوى.")
        elif complaint.status == ComplaintStatus.REJECTED:
            recommended_actions.append("راجع سبب الرفض وتأكد من تسجيله بوضوح في النظام.")
            recommended_actions.append("أبلغ مقدم الشكوى رسمياً بقرار الرفض ومبرراته.")
    else:
        if complaint.status == ComplaintStatus.NEW:
            recommended_actions.append("راجع الشكوى وصنّفها (نوع، أولوية، منطقة) خلال 24 ساعة.")
        if related_task is None:
            recommended_actions.append("أنشئ مهمة تنفيذية وأسندها للجهة المسؤولة فوراً.")
        elif related_task.status in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
            if age_days >= 3:
                recommended_actions.append(
                    f"تابع المهمة «{related_task.title}» — لم يبدأ التنفيذ بعد مرور {age_days} يوم."
                )
            else:
                recommended_actions.append(
                    f"تحقق من أن الفريق المسؤول استلم المهمة «{related_task.title}» وبدأ التخطيط."
                )
        if complaint.priority in (ComplaintPriority.URGENT,):
            recommended_actions.append("⚠ شكوى عاجلة — أبلغ المسؤول المباشر الآن ولا تُأجّل.")
        elif complaint.priority == ComplaintPriority.HIGH:
            recommended_actions.append("أولوية مرتفعة — أخطر المسؤول المباشر وتابع يومياً.")
        if message_count == 0:
            recommended_actions.append("افتح نقاشاً داخلياً لتنسيق العمل بين الأقسام المعنية.")
        if age_days >= 14:
            recommended_actions.append(
                f"الشكوى متأخرة جداً ({age_days} يوم) — اجمع تقريراً فورياً عن أسباب التأخير."
            )
        elif age_days >= 7:
            recommended_actions.append(
                f"مضى {age_days} أيام دون حل — وثّق أسباب التأخير واتخذ إجراءً تصعيدياً."
            )
    if not recommended_actions:
        recommended_actions.append("لا توجد إجراءات عاجلة — تابع دورياً وحدّث الحالة عند أي تقدم.")

    # ── Related items (links the UI can render) ───────────────────────
    related_items: list[RelatedItem] = []
    if related_task is not None:
        related_items.append(
            RelatedItem(type="task", id=related_task.id, label=related_task.title)
        )
    if thread is not None:
        related_items.append(
            RelatedItem(
                type="message_thread",
                id=thread.id,
                label=thread.title or f"نقاش الشكوى {complaint.tracking_number or complaint.id}",
            )
        )

    # ── Summary (one clear, human paragraph) ──────────────────────────
    type_label = _arabic_type(complaint.complaint_type)
    tracking_ref = complaint.tracking_number or f"#{complaint.id}"
    status_ar = _arabic_status(complaint.status)
    priority_ar = _arabic_priority(complaint.priority)

    summary_parts: list[str] = []

    # Opening line
    if is_open:
        if risk_level == "high":
            summary_parts.append(
                f"تنبيه: الشكوى {tracking_ref} ({type_label}) لا تزال مفتوحة وتستدعي تدخلاً عاجلاً."
            )
        else:
            summary_parts.append(
                f"الشكوى {tracking_ref} ({type_label}) قيد المعالجة حالياً."
            )
    else:
        summary_parts.append(
            f"الشكوى {tracking_ref} ({type_label}) أُغلقت بحالة: {status_ar}."
        )

    # Priority and age context
    if is_open:
        age_text = "منذ أقل من يوم" if age_days == 0 else f"منذ {age_days} يوم"
        summary_parts.append(
            f"أولويتها {priority_ar}، وقُدِّمت {age_text}."
        )

    # Location context
    if area_name:
        summary_parts.append(f"المنطقة: {area_name}.")

    # Task context
    if is_open:
        if related_task is None:
            summary_parts.append("لم يتم إنشاء مهمة تنفيذية لها حتى الآن.")
        else:
            task_status_ar = _arabic_task_status(related_task.status)
            summary_parts.append(
                f"يوجد مهمة مرتبطة «{related_task.title}» بحالة {task_status_ar}."
            )

    # Discussion context
    if message_count > 0:
        summary_parts.append(f"جرى تبادل {message_count} رسالة في النقاش الداخلي.")
    elif is_open:
        summary_parts.append("لم يُفتح نقاش داخلي بعد.")

    summary = " ".join(summary_parts)

    # Raw structured payload — kept in `data` for parity with other intents.
    data_payload: dict[str, Any] = {
        "complaint": {
            "id": complaint.id,
            "tracking_number": complaint.tracking_number,
            "status": complaint.status.value if complaint.status else None,
            "priority": complaint.priority.value if complaint.priority else None,
            "created_at": _format_dt(complaint.created_at),
            "updated_at": _format_dt(complaint.updated_at),
            "resolved_at": _format_dt(complaint.resolved_at),
            "age_days": age_days,
            "location_name": location_name,
            "area_name": area_name,
            "complaint_type": complaint.complaint_type.value if complaint.complaint_type else None,
        },
        "task": None
        if related_task is None
        else {
            "id": related_task.id,
            "title": related_task.title,
            "status": related_task.status.value if related_task.status else None,
            "priority": related_task.priority.value if related_task.priority else None,
        },
        "thread": None
        if thread is None
        else {
            "id": thread.id,
            "message_count": message_count,
            "last_message_at": _format_dt(last_message_at),
            "last_messages": last_messages,
        },
    }

    return InternalBotResponse(
        intent="context_analysis",
        summary=summary,
        data=[data_payload],
        generated_on=date.today(),
        risk_level=risk_level,
        key_points=key_points,
        recommended_actions=recommended_actions,
        related_items=related_items,
        context_type="complaint",
        context_id=complaint.id,
    )


def _arabic_type(complaint_type) -> str:
    """Return a human-readable Arabic label for a complaint type."""
    type_map = {
        "heating_network": "صيانة شبكة التدفئة",
        "corruption": "شكوى فساد",
        "infrastructure": "بنية تحتية",
        "cleaning": "نظافة",
        "electricity": "كهرباء",
        "water": "مياه",
        "roads": "طرق",
        "lighting": "إنارة",
        "other": "أخرى",
    }
    if complaint_type is None:
        return "غير محدد"
    val = complaint_type.value if hasattr(complaint_type, "value") else str(complaint_type)
    return type_map.get(val, val)


def _arabic_task_status(status) -> str:
    """Return a human-readable Arabic label for a task status."""
    if status is None:
        return "غير محددة"
    val = status.value if hasattr(status, "value") else str(status)
    return {
        "pending": "معلقة",
        "assigned": "مُسندة",
        "in_progress": "قيد التنفيذ",
        "completed": "مكتملة",
        "cancelled": "ملغاة",
    }.get(val, val)


def _infer_intent(question: str) -> BotIntent:
    q = question.strip().lower()
    if any(k in q for k in ["شكوى", "شكاوى", "complaint"]):
        return "complaints_summary"
    if any(k in q for k in ["مهمة", "مهام", "task"]):
        return "tasks_summary"
    if any(k in q for k in ["عقد", "عقود", "ينتهي", "انتهاء", "contract"]):
        return "contracts_expiring"
    raise HTTPException(status_code=422, detail="تعذّر فهم السؤال. حدّد intent أو استخدم كلمات: شكاوى/مهام/عقود.")


@router.post("/query", response_model=InternalBotResponse)
def run_internal_bot_query(
    payload: InternalBotQuery,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_internal_user),
):
    now = datetime.now(timezone.utc)

    # ── Phase-3 context-aware branch ───────────────────────────────────
    # When a context pointer is supplied, run the rule-based analysis and
    # short-circuit the rest of the intent handling.
    if payload.context_type is not None or payload.context_id is not None:
        if not payload.context_type or payload.context_id is None:
            raise HTTPException(
                status_code=422,
                detail="يجب تمرير context_type و context_id معاً.",
            )
        if payload.context_type not in SUPPORTED_CONTEXT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"نوع السياق '{payload.context_type}' غير مدعوم.",
            )

        if payload.context_type == "complaint":
            complaint = (
                db.query(Complaint).filter(Complaint.id == payload.context_id).first()
            )
            if complaint is None:
                raise HTTPException(status_code=404, detail="الشكوى غير موجودة.")
            if perms.is_sensitive_complaint(complaint) and not perms.can_view_sensitive_complaints(current_user):
                raise HTTPException(status_code=404, detail="الشكوى غير موجودة.")
            response = _build_complaint_analysis(db, complaint)
        else:  # pragma: no cover — guarded by SUPPORTED_CONTEXT_TYPES
            raise HTTPException(status_code=400, detail="نوع السياق غير مدعوم.")

        write_audit_log(
            db,
            action="internal_bot_query",
            entity_type="internal_bot",
            entity_id=payload.context_id,
            user_id=current_user.id,
            description=json.dumps(
                {
                    "intent": "context_analysis",
                    "context_type": payload.context_type,
                    "context_id": payload.context_id,
                },
                ensure_ascii=False,
            ),
            request=request,
        )
        return response

    intent: BotIntent | None = payload.intent or (_infer_intent(payload.question) if payload.question else None)
    if intent is None:
        raise HTTPException(status_code=422, detail="يجب تمرير intent أو question.")
    if intent == "context_analysis":
        raise HTTPException(
            status_code=422,
            detail="intent='context_analysis' يتطلب تمرير context_type و context_id.",
        )

    if intent == "complaints_summary":
        cutoff = now - timedelta(days=payload.days)
        query = db.query(Complaint.status, func.count(Complaint.id)).filter(Complaint.created_at >= cutoff)
        if payload.location_id:
            query = query.filter(Complaint.location_id == payload.location_id)
        if payload.project_id:
            query = query.filter(Complaint.project_id == payload.project_id)
        rows = query.group_by(Complaint.status).all()
        data = [{"status": status.value if status else "unknown", "count": count} for status, count in rows]
        total = sum(r["count"] for r in data)
        open_statuses_raw = {"new", "under_review", "assigned", "in_progress"}
        open_count = sum(r["count"] for r in data if r["status"] in open_statuses_raw)
        if total == 0:
            summary = f"لا توجد شكاوى مسجّلة خلال آخر {payload.days} يوم."
        else:
            summary = (
                f"خلال آخر {payload.days} يوم، وردت {total} شكوى إجمالاً"
                + (f"، منها {open_count} شكوى لا تزال مفتوحة." if open_count > 0 else "، وقد أُغلقت جميعها.")
            )

    elif intent == "tasks_summary":
        cutoff = now - timedelta(days=payload.days)
        query = db.query(Task.status, func.count(Task.id)).filter(Task.created_at >= cutoff)
        if payload.location_id:
            query = query.filter(Task.location_id == payload.location_id)
        if payload.project_id:
            query = query.filter(Task.project_id == payload.project_id)
        rows = query.group_by(Task.status).all()
        data = [{"status": status.value if status else "unknown", "count": count} for status, count in rows]
        total = sum(r["count"] for r in data)
        if total == 0:
            summary = f"لا توجد مهام مسجّلة خلال آخر {payload.days} يوم."
        else:
            pending_count = sum(r["count"] for r in data if r["status"] in {"pending", "assigned"})
            summary = (
                f"خلال آخر {payload.days} يوم، سُجِّلت {total} مهمة إجمالاً"
                + (f"، منها {pending_count} مهمة معلقة أو بانتظار التنفيذ." if pending_count > 0 else ".")
            )

    else:  # contracts_expiring
        end_cutoff = (now + timedelta(days=payload.days)).date()
        query = db.query(Contract.contract_number, Contract.title, Contract.end_date, Contract.status).filter(
            Contract.end_date <= end_cutoff
        )
        if payload.project_id:
            query = query.filter(Contract.project_id == payload.project_id)
        rows = query.order_by(Contract.end_date.asc()).limit(payload.limit).all()
        data = [
            {
                "contract_number": contract_number,
                "title": title,
                "end_date": end_date.isoformat() if end_date else None,
                "status": status.value if status else "unknown",
            }
            for contract_number, title, end_date, status in rows
        ]
        if len(data) == 0:
            summary = f"لا توجد عقود تنتهي خلال الـ {payload.days} يوم القادمة."
        else:
            n = len(data)
            if n == 1:
                contract_word = "عقد واحد"
            elif n == 2:
                contract_word = "عقدان"
            elif n <= 10:
                contract_word = f"{n} عقود"
            else:
                contract_word = f"{n} عقداً"
            summary = (
                f"يوجد {contract_word} ستنتهي خلال الـ {payload.days} يوم القادمة — "
                "يُنصح بمراجعتها وبدء إجراءات التجديد أو الإغلاق."
            )

    write_audit_log(
        db,
        action="internal_bot_query",
        entity_type="internal_bot",
        entity_id=None,
        user_id=current_user.id,
        description=json.dumps(
            {
                "intent": intent,
                "days": payload.days,
                "limit": payload.limit,
                "location_id": payload.location_id,
                "project_id": payload.project_id,
                "has_question": bool(payload.question),
            },
            ensure_ascii=False,
        ),
        request=request,
    )

    return InternalBotResponse(intent=intent, summary=summary, data=data, generated_on=date.today())
