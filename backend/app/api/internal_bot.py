from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_internal_user
from app.core.database import get_db
from app.models.complaint import Complaint
from app.models.contract import Contract
from app.models.task import Task
from app.models.user import User
from app.schemas.internal_bot import InternalBotQuery, InternalBotResponse

router = APIRouter(prefix="/internal-bot", tags=["internal-bot"])


@router.post("/query", response_model=InternalBotResponse)
def run_internal_bot_query(
    payload: InternalBotQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_internal_user),
):
    _ = current_user  # Explicitly force auth dependency evaluation.
    now = datetime.now(timezone.utc)

    if payload.intent == "complaints_summary":
        cutoff = now - timedelta(days=payload.days)
        rows = (
            db.query(Complaint.status, func.count(Complaint.id))
            .filter(Complaint.created_at >= cutoff)
            .group_by(Complaint.status)
            .all()
        )
        data = [{"status": status.value if status else "unknown", "count": count} for status, count in rows]
        summary = f"ملخص الشكاوى خلال آخر {payload.days} يوم."

    elif payload.intent == "tasks_summary":
        cutoff = now - timedelta(days=payload.days)
        rows = (
            db.query(Task.status, func.count(Task.id))
            .filter(Task.created_at >= cutoff)
            .group_by(Task.status)
            .all()
        )
        data = [{"status": status.value if status else "unknown", "count": count} for status, count in rows]
        summary = f"ملخص المهام خلال آخر {payload.days} يوم."

    else:  # contracts_expiring
        end_cutoff = (now + timedelta(days=payload.days)).date()
        rows = (
            db.query(Contract.contract_number, Contract.title, Contract.end_date, Contract.status)
            .filter(Contract.end_date <= end_cutoff)
            .order_by(Contract.end_date.asc())
            .limit(payload.limit)
            .all()
        )
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

    return InternalBotResponse(
        intent=payload.intent,
        summary=summary,
        data=data,
        generated_on=date.today(),
    )
