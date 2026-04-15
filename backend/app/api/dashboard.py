from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.task import Task, TaskStatus
from app.models.contract import Contract, ContractStatus
from app.models.user import User
from app.schemas.dashboard import DashboardStats, RecentActivity
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total_complaints = db.query(func.count(Complaint.id)).scalar()
    
    complaints_by_status = {}
    for status in ComplaintStatus:
        count = db.query(func.count(Complaint.id)).filter(Complaint.status == status).scalar()
        complaints_by_status[status.value] = count
    
    total_tasks = db.query(func.count(Task.id)).scalar()
    
    tasks_by_status = {}
    for status in TaskStatus:
        count = db.query(func.count(Task.id)).filter(Task.status == status).scalar()
        tasks_by_status[status.value] = count
    
    total_contracts = db.query(func.count(Contract.id)).scalar()
    active_contracts = db.query(func.count(Contract.id)).filter(Contract.status == ContractStatus.ACTIVE).scalar()
    
    threshold_date = date.today() + timedelta(days=30)
    contracts_nearing_expiry = db.query(func.count(Contract.id)).filter(
        Contract.status == ContractStatus.ACTIVE,
        Contract.end_date <= threshold_date,
        Contract.end_date >= date.today()
    ).scalar()
    
    return DashboardStats(
        total_complaints=total_complaints,
        complaints_by_status=complaints_by_status,
        total_tasks=total_tasks,
        tasks_by_status=tasks_by_status,
        total_contracts=total_contracts,
        active_contracts=active_contracts,
        contracts_nearing_expiry=contracts_nearing_expiry,
    )


@router.get("/recent-activity", response_model=RecentActivity)
def get_recent_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    recent_complaints = db.query(Complaint).order_by(Complaint.created_at.desc()).limit(5).all()
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
