"""
GIS / Operations Map API — provides unified map data for the operations dashboard.

Endpoints:
  GET  /gis/operations-map   — combined markers (complaints + tasks) with type distinction
  GET  /gis/area-boundaries  — area polygon boundaries for overlay display
  PUT  /gis/area-boundaries/{area_id}  — update area boundary (admin)
"""
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.task import Task, TaskStatus
from app.models.location import Area
from app.models.user import User, UserRole
from app.api.deps import get_current_internal_user

router = APIRouter(prefix="/gis", tags=["gis"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OperationsMapMarker(BaseModel):
    id: int
    entity_type: str  # "complaint" or "task"
    latitude: float
    longitude: float
    title: str
    status: str
    area_id: Optional[int] = None
    reference: Optional[str] = None  # tracking_number or task id
    priority: Optional[str] = None

    class Config:
        from_attributes = True


class AreaBoundary(BaseModel):
    id: int
    name: str
    name_ar: str
    code: str
    description: Optional[str] = None
    # Boundary as a list of [lat, lng] pairs forming a polygon
    boundary: Optional[List[List[float]]] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True


class AreaBoundaryUpdate(BaseModel):
    """Payload for updating an area's boundary polygon and color."""
    boundary: Optional[List[List[float]]] = None
    color: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/operations-map", response_model=List[OperationsMapMarker])
def get_operations_map(
    entity_type: Optional[str] = Query(None, description="Filter: 'complaint' or 'task'"),
    status_filter: Optional[str] = None,
    area_id: Optional[int] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """
    Return combined markers for complaints and tasks that have coordinates.
    Used by the unified operations map view.
    """
    markers: List[OperationsMapMarker] = []

    # ── Complaints ──
    if entity_type is None or entity_type == "complaint":
        q = db.query(Complaint).filter(
            Complaint.latitude.isnot(None),
            Complaint.longitude.isnot(None),
        )
        if status_filter:
            q = q.filter(Complaint.status == status_filter)
        if area_id:
            q = q.filter(Complaint.area_id == area_id)

        for c in q.order_by(Complaint.created_at.desc()).limit(500).all():
            markers.append(OperationsMapMarker(
                id=c.id,
                entity_type="complaint",
                latitude=c.latitude,
                longitude=c.longitude,
                title=c.description[:80] if c.description else "شكوى",
                status=c.status.value if c.status else "new",
                area_id=c.area_id,
                reference=c.tracking_number,
                priority=c.priority.value if c.priority else None,
            ))

    # ── Tasks ──
    if entity_type is None or entity_type == "task":
        q = db.query(Task).filter(
            Task.latitude.isnot(None),
            Task.longitude.isnot(None),
        )
        if status_filter:
            q = q.filter(Task.status == status_filter)
        if area_id:
            q = q.filter(Task.area_id == area_id)

        for t in q.order_by(Task.created_at.desc()).limit(500).all():
            markers.append(OperationsMapMarker(
                id=t.id,
                entity_type="task",
                latitude=t.latitude,
                longitude=t.longitude,
                title=t.title[:80] if t.title else "مهمة",
                status=t.status.value if t.status else "pending",
                area_id=t.area_id,
                reference=f"TSK-{t.id}",
                priority=t.priority.value if t.priority else None,
            ))

    return markers


@router.get("/area-boundaries", response_model=List[AreaBoundary])
def get_area_boundaries(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """
    Return area boundaries for map overlay display.
    Reads boundary polygons from the database (boundary_polygon + color columns).
    """
    areas = db.query(Area).all()
    result = []
    for area in areas:
        boundary = None
        if area.boundary_polygon:
            try:
                boundary = json.loads(area.boundary_polygon)
            except (json.JSONDecodeError, TypeError):
                boundary = None

        result.append(AreaBoundary(
            id=area.id,
            name=area.name,
            name_ar=area.name_ar,
            code=area.code,
            description=area.description,
            boundary=boundary,
            color=area.color,
        ))
    return result


@router.put("/area-boundaries/{area_id}", response_model=AreaBoundary)
def update_area_boundary(
    area_id: int,
    payload: AreaBoundaryUpdate,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """
    Update the boundary polygon and/or color for a specific area.
    Requires project_director role.
    """
    if current_user.role != UserRole.PROJECT_DIRECTOR:
        raise HTTPException(status_code=403, detail="Only project director can update area boundaries")

    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    if payload.boundary is not None:
        area.boundary_polygon = json.dumps(payload.boundary)
    if payload.color is not None:
        area.color = payload.color

    db.commit()
    db.refresh(area)

    boundary = None
    if area.boundary_polygon:
        try:
            boundary = json.loads(area.boundary_polygon)
        except (json.JSONDecodeError, TypeError):
            boundary = None

    return AreaBoundary(
        id=area.id,
        name=area.name,
        name_ar=area.name_ar,
        code=area.code,
        description=area.description,
        boundary=boundary,
        color=area.color,
    )
