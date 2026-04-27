"""
Locations API — operational geography engine for Dummar Project.

Provides:
- Unified Location CRUD with parent-child hierarchy
- Tree view / hierarchy navigation
- Location detail (dossier) with linked complaints, tasks, contracts
- Search and filters (type, status, parent, operational flags)
- Operational statistics and indicators per location
- Location-based reports (hotspots, delays, contract coverage)
- CSV export for location reports
- Nearby entities for map integration
- Legacy Area / Building / Street endpoints for backward compatibility
"""

import csv
import io
import json
import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.location import (
    Area, Building, Street,
    Location, LocationType, LocationStatus, ContractLocation,
)
from app.models.complaint import Complaint, ComplaintStatus
from app.models.task import Task, TaskStatus
from app.models.contract import Contract, ContractStatus as CStatus
from app.models.user import User, UserRole
from app.schemas.location import (
    # Unified
    LocationCreate, LocationUpdate, LocationResponse,
    LocationTreeNode, LocationDetail, LocationStats, LocationReportSummary,
    # Legacy
    AreaCreate, AreaUpdate, AreaResponse,
    BuildingCreate, BuildingResponse,
    StreetCreate, StreetResponse,
)
from app.api.deps import get_current_internal_user, require_role
from app.services.audit import write_audit_log
from app.services.notification_service import notify_location_event

router = APIRouter(prefix="/locations", tags=["locations"])
logger = logging.getLogger("dummar.locations")

_location_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.ENGINEER_SUPERVISOR,
    UserRole.AREA_SUPERVISOR,
)

# Statuses considered "open" for operational indicators
_OPEN_COMPLAINT_STATUSES = {
    ComplaintStatus.NEW, ComplaintStatus.UNDER_REVIEW,
    ComplaintStatus.ASSIGNED, ComplaintStatus.IN_PROGRESS,
}
_OPEN_TASK_STATUSES = {
    TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS,
}
_ACTIVE_CONTRACT_STATUSES = {CStatus.ACTIVE, CStatus.APPROVED}

# Hotspot threshold
_HOTSPOT_THRESHOLD = 5  # locations with >= this many open complaints


# ═══════════════════════════════════════════════════════════════════════════
# Unified Location endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/", response_model=LocationResponse)
def create_location(
    payload: LocationCreate,
    request: Request,
    current_user: User = Depends(_location_managers),
    db: Session = Depends(get_db),
):
    """Create a new location node in the hierarchy."""
    # Validate parent exists
    if payload.parent_id:
        parent = db.query(Location).filter(Location.id == payload.parent_id).first()
        if not parent:
            raise HTTPException(status_code=400, detail="Parent location not found")

    # Check code uniqueness
    existing = db.query(Location).filter(Location.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Location code already exists")

    loc = Location(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)

    write_audit_log(
        db, action="location_create", entity_type="location",
        entity_id=loc.id, user_id=current_user.id,
        description=f"Location '{loc.name}' ({loc.location_type}) created",
        request=request,
    )

    notify_location_event(
        db, event="location_created",
        location_id=loc.id, location_name=loc.name,
    )

    return loc


@router.get("/list", response_model=List[LocationResponse])
def list_locations(
    skip: int = 0,
    limit: int = 200,
    location_type: Optional[str] = None,
    status: Optional[str] = None,
    parent_id: Optional[int] = None,
    is_active: Optional[int] = None,
    search: Optional[str] = None,
    has_open_complaints: Optional[bool] = None,
    has_active_tasks: Optional[bool] = None,
    has_contract_coverage: Optional[bool] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """List locations with filtering and search."""
    query = db.query(Location)

    if location_type:
        query = query.filter(Location.location_type == location_type)
    if status:
        query = query.filter(Location.status == status)
    if parent_id is not None:
        if parent_id == 0:
            query = query.filter(Location.parent_id.is_(None))
        else:
            query = query.filter(Location.parent_id == parent_id)
    if is_active is not None:
        query = query.filter(Location.is_active == is_active)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Location.name.ilike(term),
                Location.code.ilike(term),
                Location.description.ilike(term),
            )
        )

    # Operational filters (subquery-based)
    if has_open_complaints:
        subq = (
            db.query(Complaint.location_id)
            .filter(Complaint.status.in_([s.value for s in _OPEN_COMPLAINT_STATUSES]))
            .distinct()
            .subquery()
        )
        query = query.filter(Location.id.in_(db.query(subq)))

    if has_active_tasks:
        subq = (
            db.query(Task.location_id)
            .filter(Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]))
            .distinct()
            .subquery()
        )
        query = query.filter(Location.id.in_(db.query(subq)))

    if has_contract_coverage:
        subq = (
            db.query(ContractLocation.location_id)
            .join(Contract, Contract.id == ContractLocation.contract_id)
            .filter(Contract.status.in_([s.value for s in _ACTIVE_CONTRACT_STATUSES]))
            .distinct()
            .subquery()
        )
        query = query.filter(Location.id.in_(db.query(subq)))

    locations = query.order_by(Location.name).offset(skip).limit(limit).all()
    return locations


@router.get("/tree", response_model=List[LocationTreeNode])
def get_location_tree(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Return the full location hierarchy as a tree."""
    all_locations = db.query(Location).filter(Location.is_active == 1).order_by(Location.name).all()

    # Pre-compute counts
    complaint_counts = dict(
        db.query(Complaint.location_id, func.count(Complaint.id))
        .filter(Complaint.location_id.isnot(None))
        .group_by(Complaint.location_id)
        .all()
    )
    task_counts = dict(
        db.query(Task.location_id, func.count(Task.id))
        .filter(Task.location_id.isnot(None))
        .group_by(Task.location_id)
        .all()
    )
    contract_counts = dict(
        db.query(ContractLocation.location_id, func.count(ContractLocation.id))
        .group_by(ContractLocation.location_id)
        .all()
    )

    # Build tree
    node_map = {}
    for loc in all_locations:
        node_map[loc.id] = LocationTreeNode(
            id=loc.id,
            name=loc.name,
            code=loc.code,
            location_type=loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type),
            parent_id=loc.parent_id,
            status=loc.status.value if hasattr(loc.status, 'value') else str(loc.status),
            is_active=loc.is_active,
            children=[],
            complaint_count=complaint_counts.get(loc.id, 0),
            task_count=task_counts.get(loc.id, 0),
            contract_count=contract_counts.get(loc.id, 0),
        )

    roots = []
    for loc in all_locations:
        node = node_map[loc.id]
        if loc.parent_id and loc.parent_id in node_map:
            node_map[loc.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


@router.get("/detail/{location_id}", response_model=LocationDetail)
def get_location_detail(
    location_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Return a rich location dossier with all operational context."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    loc_resp = _location_to_response(loc)

    # Parent
    parent_resp = None
    if loc.parent_id:
        parent = db.query(Location).filter(Location.id == loc.parent_id).first()
        if parent:
            parent_resp = _location_to_response(parent)

    # Children
    children = db.query(Location).filter(Location.parent_id == location_id).order_by(Location.name).all()
    children_resp = [_location_to_response(c) for c in children]

    # Breadcrumb (walk up the tree)
    breadcrumb = []
    current = loc
    visited = set()
    while current.parent_id and current.parent_id not in visited:
        visited.add(current.id)
        current = db.query(Location).filter(Location.id == current.parent_id).first()
        if current:
            breadcrumb.insert(0, _location_to_response(current))
        else:
            break

    # Collect IDs of this location and all descendants for aggregate stats
    descendant_ids = _get_descendant_ids(db, location_id)
    all_ids = [location_id] + descendant_ids

    # Complaints
    complaint_count = db.query(func.count(Complaint.id)).filter(
        Complaint.location_id.in_(all_ids)
    ).scalar() or 0
    open_complaint_count = db.query(func.count(Complaint.id)).filter(
        Complaint.location_id.in_(all_ids),
        Complaint.status.in_([s.value for s in _OPEN_COMPLAINT_STATUSES]),
    ).scalar() or 0

    # Tasks
    task_count = db.query(func.count(Task.id)).filter(
        Task.location_id.in_(all_ids)
    ).scalar() or 0
    open_task_count = db.query(func.count(Task.id)).filter(
        Task.location_id.in_(all_ids),
        Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
    ).scalar() or 0

    # Delayed tasks
    today = date.today()
    delayed_task_count = db.query(func.count(Task.id)).filter(
        Task.location_id.in_(all_ids),
        Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
        Task.due_date.isnot(None),
        Task.due_date < today,
    ).scalar() or 0

    # Contracts
    contract_count = db.query(func.count(ContractLocation.id)).filter(
        ContractLocation.location_id.in_(all_ids)
    ).scalar() or 0
    active_contract_count = (
        db.query(func.count(ContractLocation.id))
        .join(Contract, Contract.id == ContractLocation.contract_id)
        .filter(
            ContractLocation.location_id.in_(all_ids),
            Contract.status.in_([s.value for s in _ACTIVE_CONTRACT_STATUSES]),
        )
        .scalar() or 0
    )

    return LocationDetail(
        location=loc_resp,
        parent=parent_resp,
        children=children_resp,
        breadcrumb=breadcrumb,
        complaint_count=complaint_count,
        open_complaint_count=open_complaint_count,
        task_count=task_count,
        open_task_count=open_task_count,
        contract_count=contract_count,
        active_contract_count=active_contract_count,
        delayed_task_count=delayed_task_count,
    )


@router.get("/detail/{location_id}/complaints")
def get_location_complaints(
    location_id: int,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Get complaints linked to this location (and descendants)."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    all_ids = [location_id] + _get_descendant_ids(db, location_id)
    query = db.query(Complaint).filter(Complaint.location_id.in_(all_ids))
    if status_filter:
        query = query.filter(Complaint.status == status_filter)

    total = query.count()
    items = query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total_count": total,
        "items": [
            {
                "id": c.id,
                "tracking_number": c.tracking_number,
                "full_name": c.full_name,
                "complaint_type": c.complaint_type.value if c.complaint_type else None,
                "status": c.status.value if c.status else None,
                "priority": c.priority.value if c.priority else None,
                "description": c.description,
                "created_at": str(c.created_at) if c.created_at else None,
            }
            for c in items
        ],
    }


@router.get("/detail/{location_id}/tasks")
def get_location_tasks(
    location_id: int,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Get tasks linked to this location (and descendants)."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    all_ids = [location_id] + _get_descendant_ids(db, location_id)
    query = db.query(Task).filter(Task.location_id.in_(all_ids))
    if status_filter:
        query = query.filter(Task.status == status_filter)

    total = query.count()
    items = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total_count": total,
        "items": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status.value if t.status else None,
                "priority": t.priority.value if t.priority else None,
                "due_date": str(t.due_date) if t.due_date else None,
                "created_at": str(t.created_at) if t.created_at else None,
            }
            for t in items
        ],
    }


@router.get("/detail/{location_id}/contracts")
def get_location_contracts(
    location_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Get contracts covering this location (and descendants)."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    all_ids = [location_id] + _get_descendant_ids(db, location_id)
    contract_ids = (
        db.query(ContractLocation.contract_id)
        .filter(ContractLocation.location_id.in_(all_ids))
        .distinct()
        .all()
    )
    cids = [c[0] for c in contract_ids]

    if not cids:
        return {"total_count": 0, "items": []}

    query = db.query(Contract).filter(Contract.id.in_(cids))
    total = query.count()
    items = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total_count": total,
        "items": [
            {
                "id": c.id,
                "contract_number": c.contract_number,
                "title": c.title,
                "contractor_name": c.contractor_name,
                "status": c.status.value if c.status else None,
                "contract_type": c.contract_type.value if c.contract_type else None,
                "start_date": str(c.start_date) if c.start_date else None,
                "end_date": str(c.end_date) if c.end_date else None,
            }
            for c in items
        ],
    }


@router.get("/detail/{location_id}/activity")
def get_location_activity(
    location_id: int,
    limit: int = 20,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Get recent activity timeline for a location (complaints + tasks combined)."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    all_ids = [location_id] + _get_descendant_ids(db, location_id)

    # Recent complaints
    recent_complaints = (
        db.query(Complaint)
        .filter(Complaint.location_id.in_(all_ids))
        .order_by(Complaint.created_at.desc())
        .limit(limit)
        .all()
    )

    # Recent tasks
    recent_tasks = (
        db.query(Task)
        .filter(Task.location_id.in_(all_ids))
        .order_by(Task.created_at.desc())
        .limit(limit)
        .all()
    )

    # Merge and sort by created_at
    timeline = []
    for c in recent_complaints:
        timeline.append({
            "type": "complaint",
            "id": c.id,
            "title": c.description[:80] if c.description else "شكوى",
            "reference": c.tracking_number,
            "status": c.status.value if c.status else None,
            "created_at": str(c.created_at) if c.created_at else None,
        })
    for t in recent_tasks:
        timeline.append({
            "type": "task",
            "id": t.id,
            "title": t.title[:80] if t.title else "مهمة",
            "reference": f"TSK-{t.id}",
            "status": t.status.value if t.status else None,
            "created_at": str(t.created_at) if t.created_at else None,
        })

    timeline.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return timeline[:limit]


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: int,
    payload: LocationUpdate,
    request: Request,
    current_user: User = Depends(_location_managers),
    db: Session = Depends(get_db),
):
    """Update an existing location."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Validate code uniqueness if changing
    if "code" in update_data and update_data["code"] != loc.code:
        existing = db.query(Location).filter(Location.code == update_data["code"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="Location code already exists")

    # Prevent circular parent reference
    if "parent_id" in update_data and update_data["parent_id"]:
        if update_data["parent_id"] == location_id:
            raise HTTPException(status_code=400, detail="Location cannot be its own parent")
        desc_ids = _get_descendant_ids(db, location_id)
        if update_data["parent_id"] in desc_ids:
            raise HTTPException(status_code=400, detail="Cannot set a descendant as parent")

    for field, value in update_data.items():
        setattr(loc, field, value)

    db.commit()
    db.refresh(loc)

    write_audit_log(
        db, action="location_update", entity_type="location",
        entity_id=loc.id, user_id=current_user.id,
        description=f"Location '{loc.name}' updated: {list(update_data.keys())}",
        request=request,
    )

    return loc


@router.delete("/{location_id}")
def delete_location(
    location_id: int,
    request: Request,
    current_user: User = Depends(_location_managers),
    db: Session = Depends(get_db),
):
    """Soft-delete a location (set is_active=0). Only project_director can delete."""
    if current_user.role != UserRole.PROJECT_DIRECTOR:
        raise HTTPException(status_code=403, detail="Only project director can delete locations")

    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    loc.is_active = 0
    loc.status = LocationStatus.INACTIVE
    db.commit()

    write_audit_log(
        db, action="location_delete", entity_type="location",
        entity_id=loc.id, user_id=current_user.id,
        description=f"Location '{loc.name}' deactivated",
        request=request,
    )

    return {"message": "Location deactivated", "id": location_id}


# ═══════════════════════════════════════════════════════════════════════════
# Operational Statistics & Reports
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/stats/all", response_model=List[LocationStats])
def get_all_location_stats(
    location_type: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Get operational statistics for all active locations."""
    query = db.query(Location).filter(Location.is_active == 1)
    if location_type:
        query = query.filter(Location.location_type == location_type)

    locations = query.order_by(Location.name).all()
    today = date.today()
    result = []

    for loc in locations:
        cc = db.query(func.count(Complaint.id)).filter(Complaint.location_id == loc.id).scalar() or 0
        occ = db.query(func.count(Complaint.id)).filter(
            Complaint.location_id == loc.id,
            Complaint.status.in_([s.value for s in _OPEN_COMPLAINT_STATUSES]),
        ).scalar() or 0
        tc = db.query(func.count(Task.id)).filter(Task.location_id == loc.id).scalar() or 0
        otc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
        ).scalar() or 0
        dtc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
            Task.due_date.isnot(None),
            Task.due_date < today,
        ).scalar() or 0
        coc = db.query(func.count(ContractLocation.id)).filter(
            ContractLocation.location_id == loc.id
        ).scalar() or 0
        acc = (
            db.query(func.count(ContractLocation.id))
            .join(Contract, Contract.id == ContractLocation.contract_id)
            .filter(
                ContractLocation.location_id == loc.id,
                Contract.status.in_([s.value for s in _ACTIVE_CONTRACT_STATUSES]),
            )
            .scalar() or 0
        )

        result.append(LocationStats(
            location_id=loc.id,
            location_name=loc.name,
            location_type=loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type),
            complaint_count=cc,
            open_complaint_count=occ,
            task_count=tc,
            open_task_count=otc,
            contract_count=coc,
            active_contract_count=acc,
            delayed_task_count=dtc,
            is_hotspot=occ >= _HOTSPOT_THRESHOLD,
        ))

    return result


@router.get("/reports/summary", response_model=LocationReportSummary)
def get_location_report_summary(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Management report: location-based operational intelligence."""
    all_locations = db.query(Location).filter(Location.is_active == 1).all()
    total = len(all_locations)
    today = date.today()

    # By type counts
    by_type = {}
    for loc in all_locations:
        lt = loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type)
        by_type[lt] = by_type.get(lt, 0) + 1

    # Compute stats for each location
    stats_list = []
    for loc in all_locations:
        cc = db.query(func.count(Complaint.id)).filter(Complaint.location_id == loc.id).scalar() or 0
        occ = db.query(func.count(Complaint.id)).filter(
            Complaint.location_id == loc.id,
            Complaint.status.in_([s.value for s in _OPEN_COMPLAINT_STATUSES]),
        ).scalar() or 0
        tc = db.query(func.count(Task.id)).filter(Task.location_id == loc.id).scalar() or 0
        otc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
        ).scalar() or 0
        dtc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
            Task.due_date.isnot(None),
            Task.due_date < today,
        ).scalar() or 0
        coc = db.query(func.count(ContractLocation.id)).filter(
            ContractLocation.location_id == loc.id
        ).scalar() or 0
        acc = (
            db.query(func.count(ContractLocation.id))
            .join(Contract, Contract.id == ContractLocation.contract_id)
            .filter(
                ContractLocation.location_id == loc.id,
                Contract.status.in_([s.value for s in _ACTIVE_CONTRACT_STATUSES]),
            )
            .scalar() or 0
        )

        s = LocationStats(
            location_id=loc.id,
            location_name=loc.name,
            location_type=loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type),
            complaint_count=cc,
            open_complaint_count=occ,
            task_count=tc,
            open_task_count=otc,
            contract_count=coc,
            active_contract_count=acc,
            delayed_task_count=dtc,
            is_hotspot=occ >= _HOTSPOT_THRESHOLD,
        )
        stats_list.append(s)

    # Hotspots: locations with most open complaints
    hotspots = sorted(
        [s for s in stats_list if s.is_hotspot],
        key=lambda x: x.open_complaint_count,
        reverse=True,
    )[:10]

    # Most complaints (total)
    most_complaints = sorted(stats_list, key=lambda x: x.complaint_count, reverse=True)[:10]

    # Most delayed tasks
    most_delayed = sorted(stats_list, key=lambda x: x.delayed_task_count, reverse=True)[:10]
    most_delayed = [s for s in most_delayed if s.delayed_task_count > 0]

    # Active contract coverage
    contract_coverage = sorted(stats_list, key=lambda x: x.active_contract_count, reverse=True)[:10]
    contract_coverage = [s for s in contract_coverage if s.active_contract_count > 0]

    return LocationReportSummary(
        total_locations=total,
        by_type=by_type,
        hotspots=hotspots,
        most_complaints=most_complaints,
        most_delayed=most_delayed,
        contract_coverage=contract_coverage,
    )


@router.post("/contracts/link")
def link_contract_to_location(
    contract_id: int,
    location_id: int,
    request: Request,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Link a contract to a location for coverage tracking."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    # Check duplicate
    existing = db.query(ContractLocation).filter(
        ContractLocation.contract_id == contract_id,
        ContractLocation.location_id == location_id,
    ).first()
    if existing:
        return {"message": "Link already exists", "id": existing.id}

    link = ContractLocation(contract_id=contract_id, location_id=location_id)
    db.add(link)
    db.commit()
    db.refresh(link)

    write_audit_log(
        db, action="contract_location_link", entity_type="contract_location",
        entity_id=link.id, user_id=current_user.id,
        description=f"Contract {contract_id} linked to location {location_id}",
        request=request,
    )

    notify_location_event(
        db, event="location_contract_linked",
        location_id=location_id, location_name=loc.name,
        details=f"عقد #{contract_id}",
    )

    return {"message": "Contract linked to location", "id": link.id}


@router.delete("/contracts/link")
def unlink_contract_from_location(
    contract_id: int,
    location_id: int,
    request: Request,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Remove a contract-location link."""
    link = db.query(ContractLocation).filter(
        ContractLocation.contract_id == contract_id,
        ContractLocation.location_id == location_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    db.delete(link)
    db.commit()

    write_audit_log(
        db, action="contract_location_unlink", entity_type="contract_location",
        entity_id=link.id, user_id=current_user.id,
        description=f"Contract {contract_id} unlinked from location {location_id}",
        request=request,
    )

    return {"message": "Link removed"}


# ═══════════════════════════════════════════════════════════════════════════
# CSV Export
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/reports/export/csv")
def export_location_report_csv(
    location_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Export location report data as CSV. Respects active filters."""
    query = db.query(Location).filter(Location.is_active == 1)
    if location_type:
        query = query.filter(Location.location_type == location_type)
    if status:
        query = query.filter(Location.status == status)

    locations = query.order_by(Location.name).all()
    today = date.today()

    output = io.StringIO()
    # BOM for Excel Arabic support
    output.write('\ufeff')
    writer = csv.writer(output)

    writer.writerow([
        "الاسم", "الرمز", "النوع", "الحالة",
        "عدد الشكاوى", "شكاوى مفتوحة", "عدد المهام", "مهام مفتوحة",
        "مهام متأخرة", "عدد العقود", "عقود نشطة", "نقطة ساخنة",
        "خط العرض", "خط الطول", "الوصف",
    ])

    type_labels = {
        "island": "جزيرة", "sector": "قطاع", "block": "بلوك",
        "building": "مبنى", "tower": "برج", "street": "شارع",
        "service_point": "نقطة خدمة", "other": "أخرى",
    }
    status_labels = {
        "active": "نشط", "inactive": "غير نشط",
        "under_construction": "قيد الإنشاء", "demolished": "مهدّم",
    }

    for loc in locations:
        lt = loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type)
        st = loc.status.value if hasattr(loc.status, 'value') else str(loc.status)

        cc = db.query(func.count(Complaint.id)).filter(Complaint.location_id == loc.id).scalar() or 0
        occ = db.query(func.count(Complaint.id)).filter(
            Complaint.location_id == loc.id,
            Complaint.status.in_([s.value for s in _OPEN_COMPLAINT_STATUSES]),
        ).scalar() or 0
        tc = db.query(func.count(Task.id)).filter(Task.location_id == loc.id).scalar() or 0
        otc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
        ).scalar() or 0
        dtc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
            Task.due_date.isnot(None),
            Task.due_date < today,
        ).scalar() or 0
        coc = db.query(func.count(ContractLocation.id)).filter(
            ContractLocation.location_id == loc.id
        ).scalar() or 0
        acc = (
            db.query(func.count(ContractLocation.id))
            .join(Contract, Contract.id == ContractLocation.contract_id)
            .filter(
                ContractLocation.location_id == loc.id,
                Contract.status.in_([s.value for s in _ACTIVE_CONTRACT_STATUSES]),
            )
            .scalar() or 0
        )

        writer.writerow([
            loc.name,
            loc.code,
            type_labels.get(lt, lt),
            status_labels.get(st, st),
            cc, occ, tc, otc, dtc, coc, acc,
            "نعم" if occ >= _HOTSPOT_THRESHOLD else "لا",
            loc.latitude or "",
            loc.longitude or "",
            loc.description or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=location_report.csv"},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Map: nearby entities for location detail
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/detail/{location_id}/map-data")
def get_location_map_data(
    location_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Return map data for a location: its point/boundary + nearby complaints/tasks."""
    loc = db.query(Location).filter(Location.id == location_id).first()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    all_ids = [location_id] + _get_descendant_ids(db, location_id)

    # Location point
    location_point = None
    if loc.latitude and loc.longitude:
        location_point = {"latitude": loc.latitude, "longitude": loc.longitude}

    # Boundary (if available)
    boundary = None
    if loc.boundary_path:
        try:
            boundary = json.loads(loc.boundary_path)
        except (json.JSONDecodeError, TypeError):
            pass

    # Children with coordinates
    children_points = []
    child_locs = db.query(Location).filter(
        Location.parent_id.in_(all_ids),
        Location.is_active == 1,
        Location.latitude.isnot(None),
        Location.longitude.isnot(None),
    ).all()
    for child in child_locs:
        cl_type = child.location_type.value if hasattr(child.location_type, 'value') else str(child.location_type)
        children_points.append({
            "id": child.id,
            "name": child.name,
            "code": child.code,
            "location_type": cl_type,
            "latitude": child.latitude,
            "longitude": child.longitude,
        })

    # Complaints with coordinates
    complaints = (
        db.query(Complaint)
        .filter(
            Complaint.location_id.in_(all_ids),
            Complaint.latitude.isnot(None),
            Complaint.longitude.isnot(None),
        )
        .order_by(Complaint.created_at.desc())
        .limit(50)
        .all()
    )
    complaint_markers = [
        {
            "id": c.id,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "title": c.description[:60] if c.description else "",
            "tracking_number": c.tracking_number,
            "status": c.status.value if c.status else None,
            "entity_type": "complaint",
        }
        for c in complaints
    ]

    # Tasks with coordinates
    tasks = (
        db.query(Task)
        .filter(
            Task.location_id.in_(all_ids),
            Task.latitude.isnot(None),
            Task.longitude.isnot(None),
        )
        .order_by(Task.created_at.desc())
        .limit(50)
        .all()
    )
    task_markers = [
        {
            "id": t.id,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "title": t.title[:60] if t.title else "",
            "reference": f"TSK-{t.id}",
            "status": t.status.value if t.status else None,
            "entity_type": "task",
        }
        for t in tasks
    ]

    return {
        "location": {
            "id": loc.id,
            "name": loc.name,
            "code": loc.code,
            "location_type": loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type),
            "point": location_point,
            "boundary": boundary,
        },
        "children": children_points,
        "complaints": complaint_markers,
        "tasks": task_markers,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Contract locations by contract (for contract detail UI)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/contracts/{contract_id}/locations")
def get_contract_locations(
    contract_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Get all locations linked to a specific contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    links = (
        db.query(ContractLocation)
        .filter(ContractLocation.contract_id == contract_id)
        .all()
    )

    locations = []
    for link in links:
        loc = db.query(Location).filter(Location.id == link.location_id).first()
        if loc:
            lt = loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type)
            st = loc.status.value if hasattr(loc.status, 'value') else str(loc.status)
            locations.append({
                "id": loc.id,
                "name": loc.name,
                "code": loc.code,
                "location_type": lt,
                "status": st,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "link_id": link.id,
                "linked_at": str(link.created_at) if link.created_at else None,
            })

    return {"contract_id": contract_id, "locations": locations}


# ═══════════════════════════════════════════════════════════════════════════
# Geo Dashboard — operational geography overview
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/geo-dashboard")
def get_geo_dashboard(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """
    Aggregated geo-dashboard data for the operational map overview.

    Returns:
    - summary: counts by type, status, total
    - hotspots: locations with >= 5 open complaints
    - all_locations: all active locations with coordinates and operational counts
    - recent_complaints: latest geo-located complaints
    - recent_tasks: latest geo-located tasks
    """
    today = date.today()

    # Summary
    total = db.query(func.count(Location.id)).filter(Location.is_active == 1).scalar() or 0
    by_type = {}
    for lt in LocationType:
        cnt = db.query(func.count(Location.id)).filter(
            Location.is_active == 1, Location.location_type == lt
        ).scalar() or 0
        if cnt > 0:
            by_type[lt.value] = cnt

    by_status = {}
    for ls in LocationStatus:
        cnt = db.query(func.count(Location.id)).filter(
            Location.is_active == 1, Location.status == ls
        ).scalar() or 0
        if cnt > 0:
            by_status[ls.value] = cnt

    # All active locations with operational counts
    locations = db.query(Location).filter(Location.is_active == 1).all()
    all_locations = []
    hotspots = []

    for loc in locations:
        lt = loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type)
        st = loc.status.value if hasattr(loc.status, 'value') else str(loc.status)

        occ = db.query(func.count(Complaint.id)).filter(
            Complaint.location_id == loc.id,
            Complaint.status.in_([s.value for s in _OPEN_COMPLAINT_STATUSES]),
        ).scalar() or 0

        otc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
        ).scalar() or 0

        dtc = db.query(func.count(Task.id)).filter(
            Task.location_id == loc.id,
            Task.status.in_([s.value for s in _OPEN_TASK_STATUSES]),
            Task.due_date.isnot(None),
            Task.due_date < today,
        ).scalar() or 0

        acc = (
            db.query(func.count(ContractLocation.id))
            .join(Contract, Contract.id == ContractLocation.contract_id)
            .filter(
                ContractLocation.location_id == loc.id,
                Contract.status.in_([s.value for s in _ACTIVE_CONTRACT_STATUSES]),
            )
            .scalar() or 0
        )

        entry = {
            "id": loc.id,
            "name": loc.name,
            "code": loc.code,
            "location_type": lt,
            "status": st,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "parent_id": loc.parent_id,
            "open_complaints": occ,
            "open_tasks": otc,
            "delayed_tasks": dtc,
            "active_contracts": acc,
            "is_hotspot": occ >= _HOTSPOT_THRESHOLD,
        }
        all_locations.append(entry)
        if occ >= _HOTSPOT_THRESHOLD:
            hotspots.append(entry)

    # Sort hotspots by open complaints desc
    hotspots.sort(key=lambda x: x["open_complaints"], reverse=True)

    # Recent geo-located complaints (last 50)
    recent_complaints = (
        db.query(Complaint)
        .filter(
            Complaint.latitude.isnot(None),
            Complaint.longitude.isnot(None),
        )
        .order_by(Complaint.created_at.desc())
        .limit(50)
        .all()
    )
    complaint_markers = [
        {
            "id": c.id,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "title": c.description[:60] if c.description else "",
            "tracking_number": c.tracking_number,
            "status": c.status.value if c.status else None,
            "entity_type": "complaint",
            "location_id": c.location_id,
        }
        for c in recent_complaints
    ]

    # Recent geo-located tasks (last 50)
    recent_tasks = (
        db.query(Task)
        .filter(
            Task.latitude.isnot(None),
            Task.longitude.isnot(None),
        )
        .order_by(Task.created_at.desc())
        .limit(50)
        .all()
    )
    task_markers = [
        {
            "id": t.id,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "title": t.title[:60] if t.title else "",
            "reference": f"TSK-{t.id}",
            "status": t.status.value if t.status else None,
            "entity_type": "task",
            "location_id": t.location_id,
        }
        for t in recent_tasks
    ]

    return {
        "summary": {
            "total_locations": total,
            "by_type": by_type,
            "by_status": by_status,
        },
        "hotspots": hotspots,
        "all_locations": all_locations,
        "recent_complaints": complaint_markers,
        "recent_tasks": task_markers,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Legacy endpoints (backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/areas", response_model=AreaResponse)
def create_area(
    area: AreaCreate,
    current_user: User = Depends(_location_managers),
    db: Session = Depends(get_db)
):
    db_area = Area(**area.model_dump())
    db.add(db_area)
    db.commit()
    db.refresh(db_area)
    return db_area


@router.get("/areas", response_model=List[AreaResponse])
def list_areas(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    areas = db.query(Area).offset(skip).limit(limit).all()
    return areas


@router.get("/areas/{area_id}", response_model=AreaResponse)
def get_area(area_id: int, db: Session = Depends(get_db)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")
    return area


@router.put("/areas/{area_id}", response_model=AreaResponse)
def update_area(
    area_id: int,
    area_update: AreaUpdate,
    current_user: User = Depends(_location_managers),
    db: Session = Depends(get_db)
):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    update_data = area_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(area, field, value)

    db.commit()
    db.refresh(area)
    return area


@router.post("/buildings", response_model=BuildingResponse)
def create_building(
    building: BuildingCreate,
    current_user: User = Depends(_location_managers),
    db: Session = Depends(get_db)
):
    db_building = Building(**building.model_dump())
    db.add(db_building)
    db.commit()
    db.refresh(db_building)
    return db_building


@router.get("/buildings", response_model=List[BuildingResponse])
def list_buildings(
    skip: int = 0,
    limit: int = 100,
    area_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(Building)
    if area_id:
        query = query.filter(Building.area_id == area_id)
    buildings = query.offset(skip).limit(limit).all()
    return buildings


@router.post("/streets", response_model=StreetResponse)
def create_street(
    street: StreetCreate,
    current_user: User = Depends(_location_managers),
    db: Session = Depends(get_db)
):
    db_street = Street(**street.model_dump())
    db.add(db_street)
    db.commit()
    db.refresh(db_street)
    return db_street


@router.get("/streets", response_model=List[StreetResponse])
def list_streets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    streets = db.query(Street).offset(skip).limit(limit).all()
    return streets


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _location_to_response(loc: Location) -> LocationResponse:
    return LocationResponse(
        id=loc.id,
        name=loc.name,
        code=loc.code,
        location_type=loc.location_type.value if hasattr(loc.location_type, 'value') else str(loc.location_type),
        parent_id=loc.parent_id,
        status=loc.status.value if hasattr(loc.status, 'value') else str(loc.status),
        description=loc.description,
        latitude=loc.latitude,
        longitude=loc.longitude,
        boundary_path=loc.boundary_path,
        metadata_json=loc.metadata_json,
        is_active=loc.is_active,
        created_at=loc.created_at,
        updated_at=loc.updated_at,
    )


def _get_descendant_ids(db: Session, location_id: int, max_depth: int = 10) -> List[int]:
    """Get all descendant location IDs (BFS, up to max_depth levels)."""
    ids = []
    current_level = [location_id]
    for _ in range(max_depth):
        children = (
            db.query(Location.id)
            .filter(Location.parent_id.in_(current_level))
            .all()
        )
        child_ids = [c[0] for c in children]
        if not child_ids:
            break
        ids.extend(child_ids)
        current_level = child_ids
    return ids
