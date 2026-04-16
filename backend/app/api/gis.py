"""
GIS / Operations Map API — provides unified map data for the operations dashboard.

Endpoints:
  GET /gis/operations-map  — combined markers (complaints + tasks) with type distinction
  GET /gis/area-boundaries — area polygon boundaries for overlay display
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.task import Task, TaskStatus
from app.models.location import Area
from app.models.user import User
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


# ---------------------------------------------------------------------------
# Dummar area boundary polygons (approximate real boundaries)
# These are simplified polygons for the Dummar project zones.
# In production, these would come from PostGIS geometry columns.
# ---------------------------------------------------------------------------

AREA_BOUNDARIES: Dict[str, Dict] = {
    "ISL-1": {
        "boundary": [
            [33.5380, 36.2185], [33.5380, 36.2210],
            [33.5365, 36.2210], [33.5365, 36.2185],
        ],
        "color": "#3B82F6",
    },
    "ISL-2": {
        "boundary": [
            [33.5365, 36.2185], [33.5365, 36.2210],
            [33.5350, 36.2210], [33.5350, 36.2185],
        ],
        "color": "#8B5CF6",
    },
    "SEC-N": {
        "boundary": [
            [33.5390, 36.2165], [33.5390, 36.2195],
            [33.5375, 36.2195], [33.5375, 36.2165],
        ],
        "color": "#10B981",
    },
    "SEC-S": {
        "boundary": [
            [33.5350, 36.2215], [33.5350, 36.2240],
            [33.5335, 36.2240], [33.5335, 36.2215],
        ],
        "color": "#F59E0B",
    },
    "CCZ": {
        "boundary": [
            [33.5360, 36.2180], [33.5360, 36.2200],
            [33.5350, 36.2200], [33.5350, 36.2180],
        ],
        "color": "#EF4444",
    },
    "SRV": {
        "boundary": [
            [33.5345, 36.2205], [33.5345, 36.2225],
            [33.5335, 36.2225], [33.5335, 36.2205],
        ],
        "color": "#06B6D4",
    },
    "GRN": {
        "boundary": [
            [33.5395, 36.2195], [33.5395, 36.2220],
            [33.5385, 36.2220], [33.5385, 36.2195],
        ],
        "color": "#22C55E",
    },
    "ADM": {
        "boundary": [
            [33.5340, 36.2170], [33.5340, 36.2190],
            [33.5330, 36.2190], [33.5330, 36.2170],
        ],
        "color": "#6366F1",
    },
}


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
    Uses pre-defined boundary polygons for Dummar project zones.
    """
    areas = db.query(Area).all()
    result = []
    for area in areas:
        boundary_info = AREA_BOUNDARIES.get(area.code, {})
        result.append(AreaBoundary(
            id=area.id,
            name=area.name,
            name_ar=area.name_ar,
            code=area.code,
            description=area.description,
            boundary=boundary_info.get("boundary"),
            color=boundary_info.get("color"),
        ))
    return result
