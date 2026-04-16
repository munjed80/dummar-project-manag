from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
from app.core.database import get_db
from app.models.task import Task, TaskActivity, TaskStatus
from app.models.user import User, UserRole
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskActivityResponse
from app.api.deps import get_current_user, require_role
from app.services.audit import write_audit_log

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Roles allowed to manage tasks
_task_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.ENGINEER_SUPERVISOR,
    UserRole.AREA_SUPERVISOR,
    UserRole.COMPLAINTS_OFFICER,
)


def _serialize_files(file_list: Optional[List[str]]) -> Optional[str]:
    """Serialize a list of file paths to a JSON string for DB storage."""
    if file_list is None:
        return None
    return json.dumps(file_list)


@router.post("/", response_model=TaskResponse)
def create_task(
    task: TaskCreate,
    current_user: User = Depends(_task_managers),
    db: Session = Depends(get_db)
):
    db_task = Task(**task.model_dump())
    
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
    
    return db_task


@router.get("/", response_model=List[TaskResponse])
def list_tasks(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[TaskStatus] = None,
    area_id: Optional[int] = None,
    assigned_to_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Task)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if area_id:
        query = query.filter(Task.area_id == area_id)
    
    if assigned_to_id:
        query = query.filter(Task.assigned_to_id == assigned_to_id)
    
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(_task_managers),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    old_status = task.status
    
    update_data = task_update.model_dump(exclude_unset=True)

    # Serialize file list fields to JSON for DB storage
    for field_name in ("before_photos", "after_photos"):
        if field_name in update_data and update_data[field_name] is not None:
            update_data[field_name] = _serialize_files(update_data[field_name])

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
    
    write_audit_log(db, action="task_update", entity_type="task", entity_id=task.id, user_id=current_user.id, description=f"Task {task.id} updated")
    
    return task


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(_task_managers),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    return {"message": "Task deleted successfully"}


@router.get("/{task_id}/activities", response_model=List[TaskActivityResponse])
def get_task_activities(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activities = db.query(TaskActivity).filter(
        TaskActivity.task_id == task_id
    ).order_by(TaskActivity.created_at.desc()).all()
    
    return activities
