from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Type
from app.core.database import get_db
from app.core.security import decode_access_token
from app.core import permissions as perms
from app.models.user import User, UserRole
from app.schemas.user import TokenData

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    
    return user


def require_role(*allowed_roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}",
            )
        return current_user
    return role_checker


def get_current_active_director(
    current_user: User = Depends(require_role(UserRole.PROJECT_DIRECTOR))
) -> User:
    return current_user


def get_current_contracts_manager(
    current_user: User = Depends(require_role(
        UserRole.PROJECT_DIRECTOR,
        UserRole.CONTRACTS_MANAGER
    ))
) -> User:
    return current_user


def get_current_complaints_officer(
    current_user: User = Depends(require_role(
        UserRole.PROJECT_DIRECTOR,
        UserRole.COMPLAINTS_OFFICER
    ))
) -> User:
    return current_user


# Internal staff who can view operational data (everyone except citizen)
_internal_staff = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
    UserRole.ENGINEER_SUPERVISOR,
    UserRole.COMPLAINTS_OFFICER,
    UserRole.AREA_SUPERVISOR,
    UserRole.FIELD_TEAM,
    UserRole.CONTRACTOR_USER,
)


def get_current_internal_user(
    current_user: User = Depends(_internal_staff),
) -> User:
    """Any authenticated internal staff member (excludes citizen role)."""
    return current_user


# ---------------------------------------------------------------------------
# Fine-grained permission dependency.
#
# Layers role + organization scope + ownership on top of get_current_user.
# When ``owner_arg`` is supplied (e.g. "complaint_id") the dependency
# additionally loads the resource via the path param and runs an instance-
# level check; out-of-scope resources return 403 (not 404) so the response
# clearly distinguishes "exists elsewhere" from "doesn't exist".
# ---------------------------------------------------------------------------

# Map each ResourceType to its ORM class for instance-level checks.
def _resource_model(resource_type: "perms.ResourceType") -> Optional[Type]:
    from app.models.complaint import Complaint
    from app.models.task import Task
    from app.models.contract import Contract
    from app.models.project import Project
    from app.models.user import User as UserModel

    return {
        perms.ResourceType.COMPLAINT: Complaint,
        perms.ResourceType.TASK: Task,
        perms.ResourceType.CONTRACT: Contract,
        perms.ResourceType.PROJECT: Project,
        perms.ResourceType.USER: UserModel,
    }.get(resource_type)


def require_permission(
    action: "perms.Action",
    resource_type: "perms.ResourceType",
    *,
    owner_arg: Optional[str] = None,
):
    """Return a FastAPI dependency that enforces a fine-grained permission.

    If ``owner_arg`` is provided, it must match a path parameter name on the
    endpoint (e.g. ``"complaint_id"``); the dependency loads the resource
    and authorizes against the instance (org scope + ownership). When the
    resource doesn't exist the dependency raises 404; when it exists but the
    user can't reach it, 403 — matching standard REST semantics.
    """
    def checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        resource = None
        if owner_arg is not None:
            raw_id = request.path_params.get(owner_arg)
            try:
                resource_id = int(raw_id) if raw_id is not None else None
            except (TypeError, ValueError):
                resource_id = None
            model = _resource_model(resource_type)
            if model is None or resource_id is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Misconfigured permission check",
                )
            resource = db.query(model).filter(model.id == resource_id).first()
            if resource is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{resource_type.value} not found",
                )

        if not perms.authorize(
            db, current_user, action, resource_type, resource=resource
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied for action={action.value} "
                    f"resource={resource_type.value}"
                ),
            )
        return current_user

    return checker
