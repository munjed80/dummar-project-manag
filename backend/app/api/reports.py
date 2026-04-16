from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintStatus, ComplaintType
from app.models.task import Task, TaskStatus
from app.models.contract import Contract, ContractStatus
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def get_reports_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    month_start = today.replace(day=1)

    total_complaints = db.query(func.count(Complaint.id)).scalar() or 0
    resolved_complaints = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.status == ComplaintStatus.RESOLVED)
        .scalar()
        or 0
    )
    complaints_this_month = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.created_at >= month_start)
        .scalar()
        or 0
    )

    complaints_by_type: dict[str, int] = {}
    for ct in ComplaintType:
        count = (
            db.query(func.count(Complaint.id))
            .filter(Complaint.complaint_type == ct)
            .scalar()
            or 0
        )
        complaints_by_type[ct.value] = count

    complaints_by_status: dict[str, int] = {}
    for cs in ComplaintStatus:
        count = (
            db.query(func.count(Complaint.id))
            .filter(Complaint.status == cs)
            .scalar()
            or 0
        )
        complaints_by_status[cs.value] = count

    total_tasks = db.query(func.count(Task.id)).scalar() or 0
    completed_tasks = (
        db.query(func.count(Task.id))
        .filter(Task.status == TaskStatus.COMPLETED)
        .scalar()
        or 0
    )
    overdue_tasks = (
        db.query(func.count(Task.id))
        .filter(Task.due_date < today, Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]))
        .scalar()
        or 0
    )

    tasks_by_status: dict[str, int] = {}
    for ts in TaskStatus:
        count = (
            db.query(func.count(Task.id))
            .filter(Task.status == ts)
            .scalar()
            or 0
        )
        tasks_by_status[ts.value] = count

    total_contracts = db.query(func.count(Contract.id)).scalar() or 0
    active_contracts = (
        db.query(func.count(Contract.id))
        .filter(Contract.status == ContractStatus.ACTIVE)
        .scalar()
        or 0
    )
    total_contract_value = (
        db.query(func.sum(Contract.contract_value)).scalar() or 0
    )

    return {
        "complaints": {
            "total": total_complaints,
            "resolved": resolved_complaints,
            "this_month": complaints_this_month,
            "resolution_rate": round(
                (resolved_complaints / total_complaints * 100)
                if total_complaints
                else 0,
                1,
            ),
            "by_type": complaints_by_type,
            "by_status": complaints_by_status,
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "overdue": overdue_tasks,
            "completion_rate": round(
                (completed_tasks / total_tasks * 100) if total_tasks else 0, 1
            ),
            "by_status": tasks_by_status,
        },
        "contracts": {
            "total": total_contracts,
            "active": active_contracts,
            "total_value": float(total_contract_value),
        },
    }
