import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_internal_user
from app.core.database import get_db
from app.models.complaint import Complaint
from app.models.contract import Contract
from app.models.task import Task
from app.models.user import User
from app.schemas.internal_bot import BotIntent, InternalBotQuery, InternalBotResponse
from app.services.audit import write_audit_log

router = APIRouter(prefix="/internal-bot", tags=["internal-bot"])


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
    intent: BotIntent | None = payload.intent or (_infer_intent(payload.question) if payload.question else None)
    if intent is None:
        raise HTTPException(status_code=422, detail="يجب تمرير intent أو question.")

    if intent == "complaints_summary":
        cutoff = now - timedelta(days=payload.days)
        query = db.query(Complaint.status, func.count(Complaint.id)).filter(Complaint.created_at >= cutoff)
        if payload.location_id:
            query = query.filter(Complaint.location_id == payload.location_id)
        if payload.project_id:
            query = query.filter(Complaint.project_id == payload.project_id)
        rows = query.group_by(Complaint.status).all()
        data = [{"status": status.value if status else "unknown", "count": count} for status, count in rows]
        summary = f"ملخص الشكاوى خلال آخر {payload.days} يوم."

    elif intent == "tasks_summary":
        cutoff = now - timedelta(days=payload.days)
        query = db.query(Task.status, func.count(Task.id)).filter(Task.created_at >= cutoff)
        if payload.location_id:
            query = query.filter(Task.location_id == payload.location_id)
        if payload.project_id:
            query = query.filter(Task.project_id == payload.project_id)
        rows = query.group_by(Task.status).all()
        data = [{"status": status.value if status else "unknown", "count": count} for status, count in rows]
        summary = f"ملخص المهام خلال آخر {payload.days} يوم."

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
        summary = f"العقود التي ستنتهي خلال {payload.days} يوم (حد أقصى {payload.limit})."

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
