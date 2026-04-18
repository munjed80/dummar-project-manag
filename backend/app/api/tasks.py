from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
import logging
from app.core.database import get_db
from app.models.task import Task, TaskActivity, TaskStatus, TaskPriority
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskActivityResponse
from app.schemas.report import PaginatedTasks
from app.api.deps import get_current_user, require_role, get_current_internal_user
from app.services.audit import write_audit_log
from app.services.notification_service import notify_task_assigned
from app.schemas.file_utils import serialize_file_list
from app.services.location_service import infer_location_id

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger("dummar.tasks")

# Roles allowed to manage tasks
_task_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.ENGINEER_SUPERVISOR,
    UserRole.AREA_SUPERVISOR,
    UserRole.COMPLAINTS_OFFICER,
)


@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    request: Request,
    current_user: User = Depends(_task_managers),
    db: Session = Depends(get_db)
):
    task_data = task.model_dump()

    # Auto-assign location_id if not explicitly provided
    resolved_location_id = infer_location_id(
        db,
        explicit_location_id=task_data.get("location_id"),
        area_id=task_data.get("area_id"),
        latitude=task_data.get("latitude"),
        longitude=task_data.get("longitude"),
    )
    task_data["location_id"] = resolved_location_id

    db_task = Task(**task_data)
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    activity = TaskActivity(
        task_id=db_task.id,
        user_id=current_user.id,
        action="created",
        description=f"Task created by {current_user.full_name}",
    )
    db.add(activity)
    db.commit()

    write_audit_log(
        db, action="task_create", entity_type="task",
        entity_id=db_task.id, user_id=current_user.id,
        description=f"Task '{db_task.title}' created",
        request=request,
    )

    # Notify assigned user
    if db_task.assigned_to_id:
        try:
            notify_task_assigned(
                db=db,
                task_id=db_task.id,
                task_title=db_task.title,
                assigned_to_id=db_task.assigned_to_id,
            )
        except Exception:
            logger.exception("Notification failed for task %d assignment", db_task.id)
    
    return db_task


@router.get("/", response_model=PaginatedTasks)
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TaskStatus] = None,
    priority_filter: Optional[TaskPriority] = None,
    area_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    query = db.query(Task)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    if area_id:
        query = query.filter(Task.area_id == area_id)
    
    if assigned_to_id:
        query = query.filter(Task.assigned_to_id == assigned_to_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term),
            )
        )
    
    total_count = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return {"total_count": total_count, "items": tasks}


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    request: Request,
    current_user: User = Depends(_task_managers),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    old_status = task.status
    old_assigned_to_id = task.assigned_to_id
    
    update_data = task_update.model_dump(exclude_unset=True)

    # Serialize file list fields to JSON for DB storage
    for field_name in ("before_photos", "after_photos"):
        if field_name in update_data and update_data[field_name] is not None:
            update_data[field_name] = serialize_file_list(update_data[field_name])

    for field, value in update_data.items():
        setattr(task, field, value)
    
    if task_update.status == TaskStatus.COMPLETED:
        task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    
    if task_update.status and old_status != task_update.status:
        activity = TaskActivity(
            task_id=task.id,
            user_id=current_user.id,
            action="status_changed",
            description=f"Status changed from {old_status.value} to {task_update.status.value}",
            old_value=old_status.value,
            new_value=task_update.status.value,
        )
        db.add(activity)
        db.commit()

        write_audit_log(
            db, action="task_status_change", entity_type="task",
            entity_id=task.id, user_id=current_user.id,
            description=f"Task {task.id} status: {old_status.value} -> {task_update.status.value}",
            request=request,
        )

    # Notify when task is assigned to a different user
    if (
        "assigned_to_id" in update_data
        and task.assigned_to_id
        and task.assigned_to_id != old_assigned_to_id
        and task.assigned_to_id != current_user.id
    ):
        try:
            notify_task_assigned(
                db=db,
                task_id=task.id,
                task_title=task.title,
                assigned_to_id=task.assigned_to_id,
            )
        except Exception:
            logger.exception("Notification failed for task %d reassignment", task.id)

    # Audit: assignment change
    if "assigned_to_id" in update_data and task.assigned_to_id != old_assigned_to_id:
        write_audit_log(
            db, action="task_assignment", entity_type="task",
            entity_id=task.id, user_id=current_user.id,
            description=f"Task {task.id} assigned: user {old_assigned_to_id} -> {task.assigned_to_id}",
            request=request,
        )
    
    write_audit_log(db, action="task_update", entity_type="task", entity_id=task.id, user_id=current_user.id, description=f"Task {task.id} updated", request=request)
    
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(_task_managers),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    write_audit_log(
        db, action="task_delete", entity_type="task",
        entity_id=task.id, user_id=current_user.id,
        description=f"Task '{task.title}' deleted",
        request=request,
    )

    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully"}


@router.get("/{task_id}/activities", response_model=List[TaskActivityResponse])
def get_task_activities(
    task_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    activities = db.query(TaskActivity).filter(
        TaskActivity.task_id == task_id
    ).order_by(TaskActivity.created_at.desc()).all()
    
    return activities
