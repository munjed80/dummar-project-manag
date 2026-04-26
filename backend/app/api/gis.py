"""
GIS / Operations Map API — provides unified map data for the operations dashboard.

Endpoints:
  GET  /gis/operations-map   — combined markers (complaints + tasks + projects + locations)
  GET  /gis/area-boundaries  — area polygon boundaries for overlay display
  PUT  /gis/area-boundaries/{area_id}  — update area boundary (admin)
"""
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.task import Task, TaskStatus
from app.models.project import Project, ProjectStatus
from app.models.location import Area, Location, LocationStatus
from app.models.user import User, UserRole
from app.api.deps import get_current_internal_user

router = APIRouter(prefix="/gis", tags=["gis"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OperationsMapMarker(BaseModel):
    id: int
    entity_type: str  # "complaint" | "task" | "project" | "location"
    latitude: float
    longitude: float
    title: str
    status: Optional[str] = None
    area_id: Optional[int] = None
    reference: Optional[str] = None  # tracking_number or task id
    priority: Optional[str] = None
    location_id: Optional[int] = None

    class Config:
        from_attributes = True


class OperationsMapUnlocatedItem(BaseModel):
    id: int
    entity_type: str
    title: str
    status: Optional[str] = None
    reference: Optional[str] = None
    location_id: Optional[int] = None
    location_text: Optional[str] = None


class OperationsMapResponse(BaseModel):
    markers: List[OperationsMapMarker]
    items_without_coordinates: List[OperationsMapUnlocatedItem]


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

@router.get("/operations-map", response_model=OperationsMapResponse)
def get_operations_map(
    entity_type: Optional[str] = Query(None, description="Filter: complaint | task | project | location"),
    status_filter: Optional[str] = None,
    area_id: Optional[int] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """
    Return combined markers for complaints, tasks, projects, and reference
    locations. Items without coordinates are returned in a separate list.
    Used by the unified operations map view.
    """
    markers: List[OperationsMapMarker] = []
    unlocated: List[OperationsMapUnlocatedItem] = []

    # ── Complaints ──
    if entity_type is None or entity_type == "complaint":
        q = db.query(Complaint)
        if status_filter:
            q = q.filter(Complaint.status == status_filter)
        if area_id:
            q = q.filter(Complaint.area_id == area_id)

        for c in q.order_by(Complaint.created_at.desc()).limit(500).all():
            item = OperationsMapUnlocatedItem(
                id=c.id,
                entity_type="complaint",
                title=c.description[:80] if c.description else "شكوى",
                status=c.status.value if c.status else "new",
                reference=c.tracking_number,
                location_id=c.location_id,
                location_text=c.location_text,
            )
            if c.latitude is not None and c.longitude is not None:
                markers.append(OperationsMapMarker(
                    id=c.id,
                    entity_type="complaint",
                    latitude=c.latitude,
                    longitude=c.longitude,
                    title=item.title,
                    status=item.status,
                    area_id=c.area_id,
                    reference=item.reference,
                    priority=c.priority.value if c.priority else None,
                    location_id=c.location_id,
                ))
            else:
                unlocated.append(item)

    # ── Tasks ──
    if entity_type is None or entity_type == "task":
        q = db.query(Task)
        if status_filter:
            q = q.filter(Task.status == status_filter)
        if area_id:
            q = q.filter(Task.area_id == area_id)

        for t in q.order_by(Task.created_at.desc()).limit(500).all():
            item = OperationsMapUnlocatedItem(
                id=t.id,
                entity_type="task",
                title=t.title[:80] if t.title else "مهمة",
                status=t.status.value if t.status else "pending",
                reference=f"TSK-{t.id}",
                location_id=t.location_id,
                location_text=t.location_text,
            )
            if t.latitude is not None and t.longitude is not None:
                markers.append(OperationsMapMarker(
                    id=t.id,
                    entity_type="task",
                    latitude=t.latitude,
                    longitude=t.longitude,
                    title=item.title,
                    status=item.status,
                    area_id=t.area_id,
                    reference=item.reference,
                    priority=t.priority.value if t.priority else None,
                    location_id=t.location_id,
                ))
            else:
                unlocated.append(item)

    # ── Projects ──
    if entity_type is None or entity_type == "project":
        q = db.query(Project).options(joinedload(Project.location))
        if status_filter:
            q = q.filter(Project.status == status_filter)

        for p in q.order_by(Project.created_at.desc()).limit(500).all():
            title = p.title[:80] if p.title else "مشروع"
            ref = p.code or f"PRJ-{p.id}"
            status = p.status.value if p.status else ProjectStatus.ACTIVE.value
            loc_lat = p.location.latitude if p.location else None
            loc_lng = p.location.longitude if p.location else None
            loc_text = p.location.name if p.location else "لا يوجد موقع مرجعي مرتبط"
            item = OperationsMapUnlocatedItem(
                id=p.id,
                entity_type="project",
                title=title,
                status=status,
                reference=ref,
                location_id=p.location_id,
                location_text=loc_text,
            )
            if loc_lat is not None and loc_lng is not None:
                markers.append(OperationsMapMarker(
                    id=p.id,
                    entity_type="project",
                    latitude=loc_lat,
                    longitude=loc_lng,
                    title=title,
                    status=status,
                    reference=ref,
                    location_id=p.location_id,
                ))
            else:
                unlocated.append(item)

    # ── Reference Locations ──
    if entity_type is None or entity_type == "location":
        q = db.query(Location).filter(Location.is_active == 1)
        if status_filter:
            q = q.filter(Location.status == status_filter)

        for loc in q.order_by(Location.name.asc()).limit(800).all():
            title = loc.name[:80] if loc.name else "موقع مرجعي"
            status = loc.status.value if loc.status else LocationStatus.ACTIVE.value
            item = OperationsMapUnlocatedItem(
                id=loc.id,
                entity_type="location",
                title=title,
                status=status,
                reference=loc.code,
                location_id=loc.id,
                location_text=loc.name,
            )
            if loc.latitude is not None and loc.longitude is not None:
                markers.append(OperationsMapMarker(
                    id=loc.id,
                    entity_type="location",
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    title=title,
                    status=status,
                    reference=loc.code,
                    location_id=loc.id,
                ))
            else:
                unlocated.append(item)

    return OperationsMapResponse(
        markers=markers,
        items_without_coordinates=unlocated,
    )


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
