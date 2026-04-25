from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from app.core.database import get_db
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.models.location import Location
from app.models.contract import Contract
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.api.deps import get_current_internal_user, require_role, get_current_user
from app.core import permissions as perms
from app.models.user import UserRole
from app.services.audit import write_audit_log

router = APIRouter(prefix="/projects", tags=["projects"])

_project_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
    UserRole.ENGINEER_SUPERVISOR,
)


@router.post("/", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    request: Request,
    current_user: User = Depends(_project_managers),
    db: Session = Depends(get_db)
):
    existing = db.query(Project).filter(Project.code == project.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project code already exists",
        )
    
    db_project = Project(
        **project.model_dump(),
        created_by_id=current_user.id,
    )
    if db_project.org_unit_id is None and current_user.org_unit_id is not None:
        db_project.org_unit_id = current_user.org_unit_id
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    write_audit_log(
        db, action="project_create", entity_type="project",
        entity_id=db_project.id, user_id=current_user.id,
        description=f"Project '{db_project.title}' created",
        request=request,
    )
    
    return _enrich_project_response(db, db_project)


@router.get("/", response_model=dict)
def list_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ProjectStatus] = None,
    location_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    query = db.query(Project)
    query = perms.scope_query(query, db, current_user, Project)

    if status:
        query = query.filter(Project.status == status)
    
    if location_id:
        query = query.filter(Project.location_id == location_id)
    
    if contract_id:
        query = query.filter(Project.contract_id == contract_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Project.title.ilike(search_term),
                Project.code.ilike(search_term),
                Project.description.ilike(search_term),
            )
        )
    
    total_count = query.count()
    projects = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    enriched = [_enrich_project_response(db, p) for p in projects]
    return {"total_count": total_count, "items": enriched}


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not perms.authorize(
        db, current_user, perms.Action.READ, perms.ResourceType.PROJECT, resource=project
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    return _enrich_project_response(db, project)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    request: Request,
    current_user: User = Depends(_project_managers),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not perms.authorize(
        db, current_user, perms.Action.UPDATE, perms.ResourceType.PROJECT, resource=project
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    
    write_audit_log(
        db, action="project_update", entity_type="project",
        entity_id=project.id, user_id=current_user.id,
        description=f"Project '{project.title}' updated",
        request=request,
    )
    
    return _enrich_project_response(db, project)


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    request: Request,
    current_user: User = Depends(require_role(UserRole.PROJECT_DIRECTOR)),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not perms.authorize(
        db, current_user, perms.Action.DELETE, perms.ResourceType.PROJECT, resource=project
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    
    write_audit_log(
        db, action="project_delete", entity_type="project",
        entity_id=project.id, user_id=current_user.id,
        description=f"Project '{project.title}' deleted",
        request=request,
    )
    
    db.delete(project)
    db.commit()
    
    return {"message": "Project deleted successfully"}


def _enrich_project_response(db: Session, project: Project) -> ProjectResponse:
    from app.models.task import Task
    from app.models.complaint import Complaint
    from app.models.team import Team
    
    task_count = db.query(func.count(Task.id)).filter(Task.project_id == project.id).scalar() or 0
    complaint_count = db.query(func.count(Complaint.id)).filter(Complaint.project_id == project.id).scalar() or 0
    team_count = db.query(func.count(Team.id)).filter(Team.project_id == project.id).scalar() or 0
    contract_count = db.query(func.count(Contract.id)).filter(Contract.project_id == project.id).scalar() or 0
    
    location_name = None
    if project.location_id:
        loc = db.query(Location).filter(Location.id == project.location_id).first()
        if loc:
            location_name = loc.name
    
    contract_number = None
    if project.contract_id:
        contract = db.query(Contract).filter(Contract.id == project.contract_id).first()
        if contract:
            contract_number = contract.contract_number
    
    return ProjectResponse(
        id=project.id,
        title=project.title,
        code=project.code,
        description=project.description,
        status=project.status,
        start_date=project.start_date,
        end_date=project.end_date,
        location_id=project.location_id,
        contract_id=project.contract_id,
        created_by_id=project.created_by_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        task_count=task_count,
        complaint_count=complaint_count,
        team_count=team_count,
        contract_count=contract_count,
        location_name=location_name,
        contract_number=contract_number,
    )
