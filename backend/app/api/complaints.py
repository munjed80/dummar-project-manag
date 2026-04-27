from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timezone
import logging
import random
import string
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.database import get_db
from app.models.complaint import Complaint, ComplaintActivity, ComplaintStatus, ComplaintPriority
from app.models.user import User, UserRole
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintResponse,
    ComplaintTrackRequest,
    ComplaintTrackResponse,
    ComplaintRepairResult,
    ComplaintActivityResponse,
)
from app.services.location_service import infer_location_id
from app.schemas.report import PaginatedComplaints
from app.api.deps import get_current_user, require_role, get_current_internal_user
from app.core import permissions as perms
from app.services.audit import write_audit_log
from app.services.notification_service import notify_complaint_status_change
from app.schemas.file_utils import serialize_file_list

router = APIRouter(prefix="/complaints", tags=["complaints"])
limiter = Limiter(key_func=get_remote_address)
logger = logging.getLogger("dummar.complaints")

# Roles allowed to manage complaints
_complaint_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.COMPLAINTS_OFFICER,
    UserRole.ENGINEER_SUPERVISOR,
    UserRole.AREA_SUPERVISOR,
)


def _coerce_task_priority(
    raw_priority: object,
    complaint_priority: object,
):
    """Map incoming complaint/task priority into TaskPriority safely."""
    from app.models.task import TaskPriority

    if raw_priority is not None:
        if isinstance(raw_priority, TaskPriority):
            return raw_priority
        if isinstance(raw_priority, str):
            try:
                return TaskPriority(raw_priority)
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid task priority '{raw_priority}'",
                ) from exc
        raise HTTPException(status_code=422, detail="Invalid task priority type")

    if complaint_priority is not None:
        # Complaint priority is an enum with matching values (low/medium/high/urgent).
        value = getattr(complaint_priority, "value", complaint_priority)
        try:
            return TaskPriority(value)
        except ValueError:
            # Fallback defensively; should not happen with current schema.
            return TaskPriority.MEDIUM

    return TaskPriority.MEDIUM


def generate_tracking_number(db: Session) -> str:
    while True:
        tracking_number = "CMP" + "".join(random.choices(string.digits, k=8))
        existing = db.query(Complaint).filter(Complaint.tracking_number == tracking_number).first()
        if not existing:
            return tracking_number


@router.post("/", response_model=ComplaintResponse)
@limiter.limit("5/minute")
def create_complaint(complaint: ComplaintCreate, request: Request, db: Session = Depends(get_db)):
    tracking_number = generate_tracking_number(db)
    
    # Auto-assign location_id if not explicitly provided
    resolved_location_id = infer_location_id(
        db,
        explicit_location_id=complaint.location_id,
        area_id=complaint.area_id,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        location_text=complaint.location_text,
    )
    
    db_complaint = Complaint(
        tracking_number=tracking_number,
        full_name=complaint.full_name,
        phone=complaint.phone,
        complaint_type=complaint.complaint_type,
        description=complaint.description,
        location_text=complaint.location_text,
        area_id=complaint.area_id,
        location_id=resolved_location_id,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        images=serialize_file_list(complaint.images),
        status=ComplaintStatus.NEW,
        priority=ComplaintPriority.MEDIUM,
    )
    
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    
    activity = ComplaintActivity(
        complaint_id=db_complaint.id,
        action="created",
        description="Complaint submitted by citizen",
    )
    db.add(activity)
    db.commit()

    # Fire automation engine for complaint_created. Errors must never break
    # the citizen-facing API, so the engine swallows its own exceptions.
    try:
        from app.models.automation import AutomationTrigger
        from app.services.automation_engine import fire_event

        fire_event(
            db,
            AutomationTrigger.COMPLAINT_CREATED,
            {
                "complaint": {
                    "id": db_complaint.id,
                    "tracking_number": db_complaint.tracking_number,
                    "complaint_type": db_complaint.complaint_type.value,
                    "status": db_complaint.status.value,
                    "priority": (
                        db_complaint.priority.value if db_complaint.priority else None
                    ),
                    "area_id": db_complaint.area_id,
                    "location_id": db_complaint.location_id,
                    "project_id": db_complaint.project_id,
                    "assigned_to_id": db_complaint.assigned_to_id,
                },
            },
        )
    except Exception:
        logger.exception(
            "Automation fan-out failed for complaint_created (tracking=%s)",
            db_complaint.tracking_number,
        )

    return db_complaint


@router.post("/track", response_model=ComplaintTrackResponse)
@limiter.limit("10/minute")
def track_complaint(track_data: ComplaintTrackRequest, request: Request, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(
        Complaint.tracking_number == track_data.tracking_number,
        Complaint.phone == track_data.phone
    ).first()
    
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found or phone number does not match",
        )

    # Surface a public-safe repair summary when the complaint is resolved
    # and a linked task captured after-repair evidence. We intentionally do
    # not expose internal fields (assignee, team, project, before photos).
    repair_result = None
    if complaint.status == ComplaintStatus.RESOLVED:
        from app.models.task import Task as _Task
        from app.schemas.file_utils import parse_file_list

        latest_task = (
            db.query(_Task)
            .filter(_Task.complaint_id == complaint.id)
            .order_by(_Task.id.desc())
            .first()
        )
        if latest_task is not None and (
            latest_task.after_photos or latest_task.notes
        ):
            repair_result = ComplaintRepairResult(
                task_status=(
                    latest_task.status.value if latest_task.status else None
                ),
                notes=latest_task.notes,
                after_photos=parse_file_list(latest_task.after_photos),
                completed_at=latest_task.completed_at,
            )

    response = ComplaintTrackResponse.model_validate(complaint)
    response.repair_result = repair_result
    return response


@router.get("/", response_model=PaginatedComplaints)
def list_complaints(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[ComplaintStatus] = None,
    area_id: Optional[int] = None,
    location_id: Optional[int] = None,
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    query = db.query(Complaint)
    query = perms.scope_query(query, db, current_user, Complaint)

    if status_filter:
        query = query.filter(Complaint.status == status_filter)
    
    if area_id:
        query = query.filter(Complaint.area_id == area_id)

    if location_id:
        query = query.filter(Complaint.location_id == location_id)

    if project_id:
        query = query.filter(Complaint.project_id == project_id)

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
    complaints = query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()
    return {"total_count": total_count, "items": complaints}


@router.get("/map/markers", response_model=List[ComplaintResponse])
def get_complaints_map_markers(
    status_filter: Optional[ComplaintStatus] = None,
    area_id: Optional[int] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Return complaints that have coordinates, for map display."""
    query = db.query(Complaint).filter(
        Complaint.latitude.isnot(None),
        Complaint.longitude.isnot(None),
    )
    query = perms.scope_query(query, db, current_user, Complaint)

    if status_filter:
        query = query.filter(Complaint.status == status_filter)

    if area_id:
        query = query.filter(Complaint.area_id == area_id)

    return query.order_by(Complaint.created_at.desc()).limit(500).all()


@router.get("/citizen/my-complaints", response_model=PaginatedComplaints)
def get_citizen_complaints(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[ComplaintStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return complaints submitted by the current citizen user.
    Matches by phone number (same as the complaint submission flow).
    """
    if not current_user.phone:
        return {"total_count": 0, "items": []}

    query = db.query(Complaint).filter(Complaint.phone == current_user.phone)

    if status_filter:
        query = query.filter(Complaint.status == status_filter)

    total_count = query.count()
    complaints = query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()
    return {"total_count": total_count, "items": complaints}


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if not perms.authorize(
        db, current_user, perms.Action.READ, perms.ResourceType.COMPLAINT, resource=complaint
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    return complaint


@router.put("/{complaint_id}", response_model=ComplaintResponse)
def update_complaint(
    complaint_id: int,
    complaint_update: ComplaintUpdate,
    request: Request,
    current_user: User = Depends(_complaint_managers),
    db: Session = Depends(get_db)
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if not perms.authorize(
        db, current_user, perms.Action.UPDATE, perms.ResourceType.COMPLAINT, resource=complaint
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    
    old_status = complaint.status
    old_assigned_to_id = complaint.assigned_to_id
    
    update_data = complaint_update.model_dump(exclude_unset=True)

    # Serialize file list fields to JSON for DB storage
    if "images" in update_data and update_data["images"] is not None:
        update_data["images"] = serialize_file_list(update_data["images"])

    for field, value in update_data.items():
        setattr(complaint, field, value)
    
    if complaint_update.status == ComplaintStatus.RESOLVED:
        complaint.resolved_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(complaint)
    
    if complaint_update.status and old_status != complaint_update.status:
        activity = ComplaintActivity(
            complaint_id=complaint.id,
            user_id=current_user.id,
            action="status_changed",
            description=f"Status changed from {old_status.value} to {complaint_update.status.value}",
            old_value=old_status.value,
            new_value=complaint_update.status.value,
        )
        db.add(activity)
        db.commit()

        # Send notifications for status change
        try:
            notify_complaint_status_change(
                db=db,
                complaint_id=complaint.id,
                tracking_number=complaint.tracking_number,
                old_status=old_status.value,
                new_status=complaint_update.status.value,
                assigned_to_id=complaint.assigned_to_id,
            )
        except Exception:
            logger.exception("Notification failed for complaint %s status change", complaint.tracking_number)

        # Fire automation engine for complaint_status_changed.
        try:
            from app.models.automation import AutomationTrigger
            from app.services.automation_engine import fire_event

            fire_event(
                db,
                AutomationTrigger.COMPLAINT_STATUS_CHANGED,
                {
                    "complaint": {
                        "id": complaint.id,
                        "tracking_number": complaint.tracking_number,
                        "complaint_type": complaint.complaint_type.value,
                        "status": complaint.status.value,
                        "priority": (
                            complaint.priority.value if complaint.priority else None
                        ),
                        "area_id": complaint.area_id,
                        "location_id": complaint.location_id,
                        "project_id": complaint.project_id,
                        "assigned_to_id": complaint.assigned_to_id,
                    },
                    "old_status": old_status.value,
                    "new_status": complaint_update.status.value,
                    "actor_user_id": current_user.id,
                },
            )
        except Exception:
            logger.exception(
                "Automation fan-out failed for complaint_status_changed (tracking=%s)",
                complaint.tracking_number,
            )

        # Audit: specific status change
        write_audit_log(
            db, action="complaint_status_change", entity_type="complaint",
            entity_id=complaint.id, user_id=current_user.id,
            description=f"Complaint {complaint.tracking_number} status: {old_status.value} -> {complaint_update.status.value}",
            request=request,
        )
    
    # Audit: assignment change
    if "assigned_to_id" in update_data and complaint.assigned_to_id != old_assigned_to_id:
        write_audit_log(
            db, action="complaint_assignment", entity_type="complaint",
            entity_id=complaint.id, user_id=current_user.id,
            description=f"Complaint {complaint.tracking_number} assigned: user {old_assigned_to_id} -> {complaint.assigned_to_id}",
            request=request,
        )

    write_audit_log(db, action="complaint_update", entity_type="complaint", entity_id=complaint.id, user_id=current_user.id, description=f"Complaint {complaint.tracking_number} updated", request=request)
    
    return complaint


@router.get("/{complaint_id}/activities", response_model=List[ComplaintActivityResponse])
def get_complaint_activities(
    complaint_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    activities = db.query(ComplaintActivity).filter(
        ComplaintActivity.complaint_id == complaint_id
    ).order_by(ComplaintActivity.created_at.desc()).all()
    
    return activities


@router.post("/{complaint_id}/create-task")
def create_task_from_complaint(
    complaint_id: int,
    request: Request,
    task_data: dict,
    current_user: User = Depends(require_role(
        UserRole.PROJECT_DIRECTOR,
        UserRole.CONTRACTS_MANAGER,
        UserRole.ENGINEER_SUPERVISOR,
        UserRole.COMPLAINTS_OFFICER,
        UserRole.AREA_SUPERVISOR,
    )),
    db: Session = Depends(get_db)
):
    from app.models.task import Task, TaskActivity, TaskPriority, TaskSourceType, TaskStatus
    from app.schemas.task import TaskResponse

    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    # Avoid duplicate task creation for the same complaint unless the caller
    # explicitly opts in via {"force": true}. An "active" task is anything
    # not in CANCELLED state — completed tasks still count, so a second
    # task implies a follow-up that the operator should consciously confirm.
    force = bool(task_data.get("force"))
    if not force:
        existing = (
            db.query(Task)
            .filter(
                Task.complaint_id == complaint.id,
                Task.status != TaskStatus.CANCELLED,
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Task #{existing.id} already exists for this complaint. "
                    "Pass force=true to create another."
                ),
            )

    assigned_to_id = task_data.get("assigned_to_id")
    team_id = task_data.get("team_id")
    if not assigned_to_id and not team_id:
        raise HTTPException(
            status_code=422,
            detail="A responsible assignee is required (assigned_to_id or team_id)",
        )
    task_priority = _coerce_task_priority(task_data.get("priority"), complaint.priority)
    if task_priority is None:
        task_priority = TaskPriority.MEDIUM

    inferred_location_id = complaint.location_id
    if inferred_location_id is None:
        inferred_location_id = infer_location_id(
            db,
            explicit_location_id=None,
            area_id=complaint.area_id,
            latitude=complaint.latitude,
            longitude=complaint.longitude,
            location_text=complaint.location_text or complaint.description,
        )

    # Create task with data from complaint
    new_task = Task(
        title=task_data.get("title", f"Task from complaint {complaint.tracking_number}"),
        description=task_data.get("description", complaint.description),
        source_type=TaskSourceType.COMPLAINT,
        complaint_id=complaint.id,
        area_id=complaint.area_id,
        location_id=inferred_location_id,
        location_text=complaint.location_text,
        latitude=complaint.latitude,
        longitude=complaint.longitude,
        priority=task_priority,
        due_date=task_data.get("due_date"),
        assigned_to_id=assigned_to_id,
        team_id=team_id,
        project_id=task_data.get("project_id"),
        before_photos=complaint.images,
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Add task activity
    task_activity = TaskActivity(
        task_id=new_task.id,
        user_id=current_user.id,
        action="created_from_complaint",
        description=f"Task created from complaint {complaint.tracking_number}",
    )
    db.add(task_activity)
    
    # Update complaint status if it was NEW or UNDER_REVIEW
    if complaint.status in [ComplaintStatus.NEW, ComplaintStatus.UNDER_REVIEW]:
        complaint.status = ComplaintStatus.ASSIGNED
        
        complaint_activity = ComplaintActivity(
            complaint_id=complaint.id,
            user_id=current_user.id,
            action="task_created",
            description=f"Task #{new_task.id} created from this complaint",
        )
        db.add(complaint_activity)
    
    db.commit()
    db.refresh(new_task)
    
    write_audit_log(
        db, action="task_create_from_complaint", entity_type="task",
        entity_id=new_task.id, user_id=current_user.id,
        description=f"Task created from complaint {complaint.tracking_number}",
        request=request,
    )
    
    return TaskResponse(
        id=new_task.id,
        title=new_task.title,
        description=new_task.description,
        source_type=new_task.source_type,
        complaint_id=new_task.complaint_id,
        contract_id=new_task.contract_id,
        team_id=new_task.team_id,
        project_id=new_task.project_id,
        assigned_to_id=new_task.assigned_to_id,
        area_id=new_task.area_id,
        location_id=new_task.location_id,
        location_text=new_task.location_text,
        latitude=new_task.latitude,
        longitude=new_task.longitude,
        due_date=new_task.due_date,
        priority=new_task.priority,
        status=new_task.status,
        before_photos=new_task.before_photos,
        after_photos=None,
        notes=new_task.notes,
        created_at=new_task.created_at,
        updated_at=new_task.updated_at,
        completed_at=new_task.completed_at,
    )
