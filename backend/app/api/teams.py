from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from app.core.database import get_db
from app.models.team import Team, TeamType
from app.models.user import User
from app.models.location import Location
from app.models.project import Project
from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse
from app.api.deps import get_current_internal_user, require_role
from app.models.user import UserRole
from app.services.audit import write_audit_log

router = APIRouter(prefix="/teams", tags=["teams"])

_team_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
    UserRole.ENGINEER_SUPERVISOR,
)


@router.post("/", response_model=TeamResponse)
def create_team(
    team: TeamCreate,
    request: Request,
    current_user: User = Depends(_team_managers),
    db: Session = Depends(get_db)
):
    db_team = Team(**team.model_dump())
    
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    
    write_audit_log(
        db, action="team_create", entity_type="team",
        entity_id=db_team.id, user_id=current_user.id,
        description=f"Team '{db_team.name}' created",
        request=request,
    )
    
    return _enrich_team_response(db, db_team)


@router.get("/active", response_model=List[TeamResponse])
def list_active_teams(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    teams = db.query(Team).filter(Team.is_active == True).order_by(Team.name).all()
    return [_enrich_team_response(db, t) for t in teams]


@router.get("/", response_model=dict)
def list_teams(
    skip: int = 0,
    limit: int = 100,
    team_type: Optional[TeamType] = None,
    is_active: Optional[bool] = None,
    project_id: Optional[int] = None,
    location_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    query = db.query(Team)
    
    if team_type:
        query = query.filter(Team.team_type == team_type)
    
    if is_active is not None:
        query = query.filter(Team.is_active == is_active)
    
    if project_id:
        query = query.filter(Team.project_id == project_id)
    
    if location_id:
        query = query.filter(Team.location_id == location_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Team.name.ilike(search_term),
                Team.contact_name.ilike(search_term),
            )
        )
    
    total_count = query.count()
    teams = query.order_by(Team.created_at.desc()).offset(skip).limit(limit).all()
    enriched = [_enrich_team_response(db, t) for t in teams]
    return {"total_count": total_count, "items": enriched}


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return _enrich_team_response(db, team)


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    team_update: TeamUpdate,
    request: Request,
    current_user: User = Depends(_team_managers),
    db: Session = Depends(get_db)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    update_data = team_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(team, field, value)
    
    db.commit()
    db.refresh(team)
    
    write_audit_log(
        db, action="team_update", entity_type="team",
        entity_id=team.id, user_id=current_user.id,
        description=f"Team '{team.name}' updated",
        request=request,
    )
    
    return _enrich_team_response(db, team)


@router.delete("/{team_id}")
def delete_team(
    team_id: int,
    request: Request,
    current_user: User = Depends(require_role(UserRole.PROJECT_DIRECTOR)),
    db: Session = Depends(get_db)
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    write_audit_log(
        db, action="team_delete", entity_type="team",
        entity_id=team.id, user_id=current_user.id,
        description=f"Team '{team.name}' deleted",
        request=request,
    )
    
    db.delete(team)
    db.commit()
    
    return {"message": "Team deleted successfully"}


def _enrich_team_response(db: Session, team: Team) -> TeamResponse:
    from app.models.task import Task
    
    task_count = db.query(func.count(Task.id)).filter(Task.team_id == team.id).scalar() or 0
    
    location_name = None
    if team.location_id:
        loc = db.query(Location).filter(Location.id == team.location_id).first()
        if loc:
            location_name = loc.name
    
    project_title = None
    if team.project_id:
        project = db.query(Project).filter(Project.id == team.project_id).first()
        if project:
            project_title = project.title
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        team_type=team.team_type,
        contact_name=team.contact_name,
        contact_phone=team.contact_phone,
        contact_email=team.contact_email,
        is_active=team.is_active,
        location_id=team.location_id,
        project_id=team.project_id,
        notes=team.notes,
        created_at=team.created_at,
        updated_at=team.updated_at,
        task_count=task_count,
        location_name=location_name,
        project_title=project_title,
    )
