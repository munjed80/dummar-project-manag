from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from datetime import date
import csv
import io

from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintType, ComplaintStatus, ComplaintPriority
from app.models.task import Task, TaskStatus, TaskSourceType, TaskPriority
from app.models.contract import Contract, ContractType, ContractStatus
from app.models.location import Area
from app.models.user import User
from app.api.deps import get_current_user, get_current_internal_user
from app.core import permissions as perms
from app.schemas.report import (
    ReportSummary,
    ComplaintSummary,
    TaskSummary,
    ContractSummary,
    StatusBreakdown,
    TypeBreakdown,
    AreaBreakdown,
    PaginatedComplaints,
    PaginatedTasks,
    PaginatedContracts,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _apply_date_filter(query, model, date_from: Optional[date], date_to: Optional[date]):
    if date_from:
        query = query.filter(model.created_at >= date_from)
    if date_to:
        query = query.filter(model.created_at <= date_to)
    return query


@router.get("/summary", response_model=ReportSummary)
def get_report_summary(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    area_id: Optional[int] = None,
    status: Optional[str] = None,
    complaint_type: Optional[ComplaintType] = None,
    contract_type: Optional[ContractType] = None,
    priority: Optional[str] = None,
    assigned_to_id: Optional[int] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    # --- Complaints ---
    c_query = db.query(Complaint)
    c_query = perms.filter_sensitive_complaints(c_query, current_user)
    c_query = _apply_date_filter(c_query, Complaint, date_from, date_to)
    if area_id:
        c_query = c_query.filter(Complaint.area_id == area_id)
    if status:
        c_query = c_query.filter(Complaint.status == status)
    if complaint_type:
        c_query = c_query.filter(Complaint.complaint_type == complaint_type)
    if priority:
        c_query = c_query.filter(Complaint.priority == priority)
    if assigned_to_id:
        c_query = c_query.filter(Complaint.assigned_to_id == assigned_to_id)

    complaint_total = c_query.count()

    c_by_status = (
        c_query.with_entities(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )
    c_by_type = (
        c_query.with_entities(Complaint.complaint_type, func.count(Complaint.id))
        .group_by(Complaint.complaint_type)
        .all()
    )
    c_by_area_q = (
        c_query.with_entities(Complaint.area_id, func.count(Complaint.id))
        .group_by(Complaint.area_id)
        .all()
    )
    area_ids = [a_id for a_id, _ in c_by_area_q if a_id is not None]
    area_names = {}
    if area_ids:
        areas = db.query(Area.id, Area.name).filter(Area.id.in_(area_ids)).all()
        area_names = {a.id: a.name for a in areas}

    c_by_area = [
        AreaBreakdown(area_id=a_id, area_name=area_names.get(a_id), count=cnt)
        for a_id, cnt in c_by_area_q
    ]

    # --- Tasks ---
    t_query = db.query(Task)
    t_query = _apply_date_filter(t_query, Task, date_from, date_to)
    if area_id:
        t_query = t_query.filter(Task.area_id == area_id)
    if status:
        t_query = t_query.filter(Task.status == status)
    if priority:
        t_query = t_query.filter(Task.priority == priority)
    if assigned_to_id:
        t_query = t_query.filter(Task.assigned_to_id == assigned_to_id)

    task_total = t_query.count()

    t_by_status = (
        t_query.with_entities(Task.status, func.count(Task.id))
        .group_by(Task.status)
        .all()
    )
    t_by_area_q = (
        t_query.with_entities(Task.area_id, func.count(Task.id))
        .group_by(Task.area_id)
        .all()
    )
    t_area_ids = [a_id for a_id, _ in t_by_area_q if a_id is not None]
    if t_area_ids:
        extra_areas = db.query(Area.id, Area.name).filter(Area.id.in_(t_area_ids)).all()
        for a in extra_areas:
            area_names.setdefault(a.id, a.name)

    t_by_area = [
        AreaBreakdown(area_id=a_id, area_name=area_names.get(a_id), count=cnt)
        for a_id, cnt in t_by_area_q
    ]

    # --- Contracts ---
    co_query = db.query(Contract)
    co_query = _apply_date_filter(co_query, Contract, date_from, date_to)
    if status:
        co_query = co_query.filter(Contract.status == status)
    if contract_type:
        co_query = co_query.filter(Contract.contract_type == contract_type)

    contract_total = co_query.count()

    co_by_status = (
        co_query.with_entities(Contract.status, func.count(Contract.id))
        .group_by(Contract.status)
        .all()
    )
    co_by_type = (
        co_query.with_entities(Contract.contract_type, func.count(Contract.id))
        .group_by(Contract.contract_type)
        .all()
    )

    return ReportSummary(
        complaints=ComplaintSummary(
            total=complaint_total,
            by_status=[StatusBreakdown(status=s.value if hasattr(s, "value") else str(s), count=c) for s, c in c_by_status],
            by_type=[TypeBreakdown(type=t.value if hasattr(t, "value") else str(t), count=c) for t, c in c_by_type],
            by_area=c_by_area,
        ),
        tasks=TaskSummary(
            total=task_total,
            by_status=[StatusBreakdown(status=s.value if hasattr(s, "value") else str(s), count=c) for s, c in t_by_status],
            by_area=t_by_area,
        ),
        contracts=ContractSummary(
            total=contract_total,
            by_status=[StatusBreakdown(status=s.value if hasattr(s, "value") else str(s), count=c) for s, c in co_by_status],
            by_type=[TypeBreakdown(type=t.value if hasattr(t, "value") else str(t), count=c) for t, c in co_by_type],
        ),
    )


@router.get("/complaints", response_model=PaginatedComplaints)
def get_complaints_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    complaint_type: Optional[ComplaintType] = None,
    status: Optional[ComplaintStatus] = None,
    area_id: Optional[int] = None,
    priority: Optional[ComplaintPriority] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = db.query(Complaint)
    query = perms.filter_sensitive_complaints(query, current_user)
    query = _apply_date_filter(query, Complaint, date_from, date_to)

    if complaint_type:
        query = query.filter(Complaint.complaint_type == complaint_type)
    if status:
        query = query.filter(Complaint.status == status)
    if area_id:
        query = query.filter(Complaint.area_id == area_id)
    if priority:
        query = query.filter(Complaint.priority == priority)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Complaint.tracking_number.ilike(search_term),
                Complaint.full_name.ilike(search_term),
                Complaint.description.ilike(search_term),
            )
        )

    total_count = query.count()
    items = query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()
    return PaginatedComplaints(total_count=total_count, items=items)


@router.get("/tasks", response_model=PaginatedTasks)
def get_tasks_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[TaskStatus] = None,
    area_id: Optional[int] = None,
    priority: Optional[TaskPriority] = None,
    assigned_to_id: Optional[int] = None,
    source_type: Optional[TaskSourceType] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    query = _apply_date_filter(query, Task, date_from, date_to)

    if status:
        query = query.filter(Task.status == status)
    if area_id:
        query = query.filter(Task.area_id == area_id)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_to_id:
        query = query.filter(Task.assigned_to_id == assigned_to_id)
    if source_type:
        query = query.filter(Task.source_type == source_type)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term),
            )
        )

    total_count = query.count()
    items = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return PaginatedTasks(total_count=total_count, items=items)


@router.get("/contracts", response_model=PaginatedContracts)
def get_contracts_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[ContractStatus] = None,
    contract_type: Optional[ContractType] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = db.query(Contract)
    query = _apply_date_filter(query, Contract, date_from, date_to)

    if status:
        query = query.filter(Contract.status == status)
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Contract.contract_number.ilike(search_term),
                Contract.title.ilike(search_term),
                Contract.contractor_name.ilike(search_term),
            )
        )

    total_count = query.count()
    items = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()
    return PaginatedContracts(total_count=total_count, items=items)


# ---------------------------------------------------------------------------
# CSV Export helpers
# ---------------------------------------------------------------------------

def _build_csv_response(rows: list, headers: list, filename: str) -> StreamingResponse:
    """Build a StreamingResponse with UTF-8 BOM CSV content."""
    output = io.StringIO()
    # UTF-8 BOM for Excel compatibility
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _complaint_query_with_filters(
    db: Session,
    date_from: Optional[date],
    date_to: Optional[date],
    complaint_type: Optional[ComplaintType],
    status: Optional[ComplaintStatus],
    area_id: Optional[int],
    priority: Optional[ComplaintPriority],
    search: Optional[str],
):
    query = db.query(Complaint)
    query = _apply_date_filter(query, Complaint, date_from, date_to)
    if complaint_type:
        query = query.filter(Complaint.complaint_type == complaint_type)
    if status:
        query = query.filter(Complaint.status == status)
    if area_id:
        query = query.filter(Complaint.area_id == area_id)
    if priority:
        query = query.filter(Complaint.priority == priority)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Complaint.tracking_number.ilike(search_term),
                Complaint.full_name.ilike(search_term),
                Complaint.description.ilike(search_term),
            )
        )
    return query


def _task_query_with_filters(
    db: Session,
    date_from: Optional[date],
    date_to: Optional[date],
    status: Optional[TaskStatus],
    area_id: Optional[int],
    priority: Optional[TaskPriority],
    assigned_to_id: Optional[int],
    source_type: Optional[TaskSourceType],
    search: Optional[str],
):
    query = db.query(Task)
    query = _apply_date_filter(query, Task, date_from, date_to)
    if status:
        query = query.filter(Task.status == status)
    if area_id:
        query = query.filter(Task.area_id == area_id)
    if priority:
        query = query.filter(Task.priority == priority)
    if assigned_to_id:
        query = query.filter(Task.assigned_to_id == assigned_to_id)
    if source_type:
        query = query.filter(Task.source_type == source_type)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term),
            )
        )
    return query


def _contract_query_with_filters(
    db: Session,
    date_from: Optional[date],
    date_to: Optional[date],
    status: Optional[ContractStatus],
    contract_type: Optional[ContractType],
    search: Optional[str],
):
    query = db.query(Contract)
    query = _apply_date_filter(query, Contract, date_from, date_to)
    if status:
        query = query.filter(Contract.status == status)
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Contract.contract_number.ilike(search_term),
                Contract.title.ilike(search_term),
                Contract.contractor_name.ilike(search_term),
            )
        )
    return query


# ---------------------------------------------------------------------------
# CSV Export endpoints
# ---------------------------------------------------------------------------

@router.get("/complaints/csv")
def export_complaints_csv(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    complaint_type: Optional[ComplaintType] = None,
    status: Optional[ComplaintStatus] = None,
    area_id: Optional[int] = None,
    priority: Optional[ComplaintPriority] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = _complaint_query_with_filters(
        db, date_from, date_to, complaint_type, status, area_id, priority, search
    )
    query = perms.filter_sensitive_complaints(query, current_user)
    items = query.order_by(Complaint.created_at.desc()).all()

    # Resolve area names
    area_ids = list({c.area_id for c in items if c.area_id})
    area_names = {}
    if area_ids:
        areas = db.query(Area.id, Area.name).filter(Area.id.in_(area_ids)).all()
        area_names = {a.id: a.name for a in areas}

    headers = [
        "رقم التتبع", "مقدم الشكوى", "الهاتف", "النوع", "الحالة",
        "الأولوية", "المنطقة", "الوصف", "الموقع", "تاريخ الإنشاء", "تاريخ الحل",
    ]
    rows = []
    for c in items:
        rows.append([
            c.tracking_number,
            c.full_name,
            c.phone,
            c.complaint_type.value if c.complaint_type else "",
            c.status.value if c.status else "",
            c.priority.value if c.priority else "",
            area_names.get(c.area_id, ""),
            c.description or "",
            c.location_text or "",
            str(c.created_at) if c.created_at else "",
            str(c.resolved_at) if c.resolved_at else "",
        ])
    return _build_csv_response(rows, headers, "complaints_report.csv")


@router.get("/tasks/csv")
def export_tasks_csv(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[TaskStatus] = None,
    area_id: Optional[int] = None,
    priority: Optional[TaskPriority] = None,
    assigned_to_id: Optional[int] = None,
    source_type: Optional[TaskSourceType] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = _task_query_with_filters(
        db, date_from, date_to, status, area_id, priority,
        assigned_to_id, source_type, search,
    )
    items = query.order_by(Task.created_at.desc()).all()

    # Resolve area names
    area_ids = list({t.area_id for t in items if t.area_id})
    area_names = {}
    if area_ids:
        areas = db.query(Area.id, Area.name).filter(Area.id.in_(area_ids)).all()
        area_names = {a.id: a.name for a in areas}

    # Resolve assigned-to user names
    user_ids = list({t.assigned_to_id for t in items if t.assigned_to_id})
    user_names = {}
    if user_ids:
        users = db.query(User.id, User.full_name).filter(User.id.in_(user_ids)).all()
        user_names = {u.id: u.full_name for u in users}

    headers = [
        "العنوان", "الوصف", "المصدر", "الحالة", "الأولوية",
        "المسؤول", "المنطقة", "تاريخ الاستحقاق", "تاريخ الإنشاء", "تاريخ الإكمال",
    ]
    rows = []
    for t in items:
        rows.append([
            t.title,
            t.description or "",
            t.source_type.value if t.source_type else "",
            t.status.value if t.status else "",
            t.priority.value if t.priority else "",
            user_names.get(t.assigned_to_id, ""),
            area_names.get(t.area_id, ""),
            str(t.due_date) if t.due_date else "",
            str(t.created_at) if t.created_at else "",
            str(t.completed_at) if t.completed_at else "",
        ])
    return _build_csv_response(rows, headers, "tasks_report.csv")


@router.get("/contracts/csv")
def export_contracts_csv(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    status: Optional[ContractStatus] = None,
    contract_type: Optional[ContractType] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = _contract_query_with_filters(
        db, date_from, date_to, status, contract_type, search
    )
    items = query.order_by(Contract.created_at.desc()).all()

    headers = [
        "رقم العقد", "العنوان", "المقاول", "النوع", "القيمة",
        "الحالة", "تاريخ البداية", "تاريخ الانتهاء", "الوصف", "تاريخ الإنشاء",
    ]
    rows = []
    for c in items:
        rows.append([
            c.contract_number,
            c.title,
            c.contractor_name,
            c.contract_type.value if c.contract_type else "",
            str(c.contract_value) if c.contract_value else "",
            c.status.value if c.status else "",
            str(c.start_date) if c.start_date else "",
            str(c.end_date) if c.end_date else "",
            c.scope_description or "",
            str(c.created_at) if c.created_at else "",
        ])
    return _build_csv_response(rows, headers, "contracts_report.csv")
