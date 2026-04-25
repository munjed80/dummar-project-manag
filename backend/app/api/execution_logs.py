"""Execution Log API — read-only view of central action telemetry.

Endpoints:
  GET /execution-logs/         — paginated list with rich filters.
  GET /execution-logs/summary  — per-bucket counts grouped by status.

Restricted to ``project_director`` (same gate as audit logs).
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.execution_log import ExecutionLog
from app.models.user import User, UserRole
from app.schemas.execution_log import PaginatedExecutionLogs

router = APIRouter(prefix="/execution-logs", tags=["execution-logs"])

_director_only = require_role(UserRole.PROJECT_DIRECTOR)


@router.get("/", response_model=PaginatedExecutionLogs)
def list_execution_logs(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    action_type: Optional[str] = None,
    action_name: Optional[str] = None,
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    current_user: User = Depends(_director_only),
    db: Session = Depends(get_db),
):
    """List execution-log entries, newest first."""
    query = db.query(ExecutionLog)

    if action_type:
        query = query.filter(ExecutionLog.action_type == action_type)
    if action_name:
        query = query.filter(ExecutionLog.action_name == action_name)
    if status:
        query = query.filter(ExecutionLog.status == status)
    if entity_type:
        query = query.filter(ExecutionLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(ExecutionLog.entity_id == entity_id)
    if user_id is not None:
        query = query.filter(ExecutionLog.user_id == user_id)
    if since is not None:
        query = query.filter(ExecutionLog.created_at >= since)
    if until is not None:
        query = query.filter(ExecutionLog.created_at <= until)

    total_count = query.count()
    items = (
        query.order_by(ExecutionLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total_count": total_count, "items": items}


@router.get("/summary")
def execution_log_summary(
    since: Optional[datetime] = None,
    current_user: User = Depends(_director_only),
    db: Session = Depends(get_db),
):
    """Return a count matrix of (action_type, status) for quick dashboards."""
    query = db.query(
        ExecutionLog.action_type,
        ExecutionLog.status,
        func.count(ExecutionLog.id).label("count"),
    )
    if since is not None:
        query = query.filter(ExecutionLog.created_at >= since)
    rows = query.group_by(ExecutionLog.action_type, ExecutionLog.status).all()

    summary: dict[str, dict[str, int]] = {}
    for action_type, status, count in rows:
        summary.setdefault(action_type, {})[status] = int(count)
    return {"by_action_type": summary}
