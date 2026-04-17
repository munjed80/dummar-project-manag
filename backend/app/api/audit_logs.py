"""
Audit Log API — read-only access to system audit trail.

Endpoints:
  GET /audit-logs/  — paginated list of audit log entries (project_director only)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.api.deps import get_current_user, require_role
from app.schemas.audit import PaginatedAuditLogs

router = APIRouter(prefix="/audit-logs", tags=["audit"])

_director_only = require_role(UserRole.PROJECT_DIRECTOR)


@router.get("/", response_model=PaginatedAuditLogs)
def list_audit_logs(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(_director_only),
    db: Session = Depends(get_db),
):
    """
    List audit log entries with optional filters.
    Restricted to project_director role.
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total_count = query.count()
    items = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    return {"total_count": total_count, "items": items}
