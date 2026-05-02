from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.task import Task, TaskStatus
from app.models.contract import Contract, ContractStatus
from app.models.investment_contract import InvestmentContract, InvestmentContractStatus
from app.models.user import User
from app.schemas.dashboard import DashboardStats, RecentActivity
from app.api.deps import get_current_user, get_current_internal_user
from app.core import permissions as perms

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    # Complaints: single GROUP BY instead of per-status queries.
    # Sensitive (corruption) complaints are excluded for non-admin users.
    complaint_base = perms.filter_sensitive_complaints(db.query(Complaint), current_user)
    complaint_counts = dict(
        complaint_base.with_entities(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )
    total_complaints = sum(complaint_counts.values())
    complaints_by_status = {
        s.value: complaint_counts.get(s, 0) for s in ComplaintStatus
    }

    # Tasks: single GROUP BY
    task_counts = dict(
        db.query(Task.status, func.count(Task.id))
        .group_by(Task.status)
        .all()
    )
    total_tasks = sum(task_counts.values())
    tasks_by_status = {
        s.value: task_counts.get(s, 0) for s in TaskStatus
    }

    # Contracts: count totals in fewer queries
    contract_counts = dict(
        db.query(Contract.status, func.count(Contract.id))
        .group_by(Contract.status)
        .all()
    )
    total_contracts = sum(contract_counts.values())
    active_contracts = contract_counts.get(ContractStatus.ACTIVE, 0)

    threshold_date = date.today() + timedelta(days=30)
    contracts_nearing_expiry = db.query(func.count(Contract.id)).filter(
        Contract.status == ContractStatus.ACTIVE,
        Contract.end_date <= threshold_date,
        Contract.end_date >= date.today()
    ).scalar()

    # Investment contracts: count expiry buckets used by the contracts page.
    today = date.today()
    inv_active = db.query(InvestmentContract).filter(
        InvestmentContract.is_active == True,
        InvestmentContract.status != InvestmentContractStatus.CANCELLED,
    )
    inv_total = inv_active.count()
    inv_expired = (
        db.query(func.count(InvestmentContract.id))
        .filter(
            InvestmentContract.is_active == True,
            InvestmentContract.status != InvestmentContractStatus.CANCELLED,
            InvestmentContract.end_date < today,
        )
        .scalar()
    )
    inv_within_30 = (
        db.query(func.count(InvestmentContract.id))
        .filter(
            InvestmentContract.is_active == True,
            InvestmentContract.status != InvestmentContractStatus.CANCELLED,
            InvestmentContract.end_date >= today,
            InvestmentContract.end_date <= today + timedelta(days=30),
        )
        .scalar()
    )
    inv_within_60 = (
        db.query(func.count(InvestmentContract.id))
        .filter(
            InvestmentContract.is_active == True,
            InvestmentContract.status != InvestmentContractStatus.CANCELLED,
            InvestmentContract.end_date >= today,
            InvestmentContract.end_date <= today + timedelta(days=60),
        )
        .scalar()
    )
    inv_within_90 = (
        db.query(func.count(InvestmentContract.id))
        .filter(
            InvestmentContract.is_active == True,
            InvestmentContract.status != InvestmentContractStatus.CANCELLED,
            InvestmentContract.end_date >= today,
            InvestmentContract.end_date <= today + timedelta(days=90),
        )
        .scalar()
    )

    return DashboardStats(
        total_complaints=total_complaints,
        complaints_by_status=complaints_by_status,
        total_tasks=total_tasks,
        tasks_by_status=tasks_by_status,
        total_contracts=total_contracts,
        active_contracts=active_contracts,
        contracts_nearing_expiry=contracts_nearing_expiry,
        total_investment_contracts=inv_total,
        investment_contracts_expired=inv_expired,
        investment_contracts_within_30=inv_within_30,
        investment_contracts_within_60=inv_within_60,
        investment_contracts_within_90=inv_within_90,
    )


@router.get("/recent-activity", response_model=RecentActivity)
def get_recent_activity(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    recent_complaints = (
        perms.filter_sensitive_complaints(db.query(Complaint), current_user)
        .order_by(Complaint.created_at.desc())
        .limit(5)
        .all()
    )
    recent_tasks = db.query(Task).order_by(Task.created_at.desc()).limit(5).all()
    recent_contracts = db.query(Contract).order_by(Contract.created_at.desc()).limit(5).all()
    
    return RecentActivity(
        recent_complaints=[{
            "id": c.id,
            "tracking_number": c.tracking_number,
            "type": c.complaint_type.value,
            "status": c.status.value,
            "created_at": c.created_at.isoformat(),
        } for c in recent_complaints],
        recent_tasks=[{
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "created_at": t.created_at.isoformat(),
        } for t in recent_tasks],
        recent_contracts=[{
            "id": c.id,
            "contract_number": c.contract_number,
            "title": c.title,
            "status": c.status.value,
            "created_at": c.created_at.isoformat(),
        } for c in recent_contracts],
    )
