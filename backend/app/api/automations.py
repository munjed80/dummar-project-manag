"""CRUD + manual-test endpoints for the automation engine."""

from __future__ import annotations

import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_internal_user, require_role
from app.core.database import get_db
from app.models.automation import Automation
from app.models.user import User, UserRole
from app.schemas.automation import (
    AutomationCreate,
    AutomationResponse,
    AutomationTestRequest,
    AutomationTestResult,
    AutomationUpdate,
)
from app.services.audit import write_audit_log
from app.services.automation_engine import run_automation

router = APIRouter(prefix="/automations", tags=["automations"])
logger = logging.getLogger("dummar.automations.api")

# Only project directors can configure automations — they can wire up
# notifications and task creation that affect the entire org.
_automation_managers = require_role(UserRole.PROJECT_DIRECTOR)


def _to_response(row: Automation) -> AutomationResponse:
    """Hydrate the JSON-encoded conditions/actions before serialising."""
    return AutomationResponse(
        id=row.id,
        name=row.name,
        description=row.description,
        trigger=row.trigger,
        conditions=json.loads(row.conditions or "[]"),
        actions=json.loads(row.actions or "[]"),
        enabled=bool(row.enabled),
        last_run_at=row.last_run_at,
        run_count=row.run_count or 0,
        last_error=row.last_error,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/", response_model=List[AutomationResponse])
def list_automations(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """List every automation. Visible to all internal staff (read-only)."""
    rows = db.query(Automation).order_by(Automation.created_at.desc()).all()
    return [_to_response(r) for r in rows]


@router.post("/", response_model=AutomationResponse, status_code=status.HTTP_201_CREATED)
def create_automation(
    payload: AutomationCreate,
    request: Request,
    current_user: User = Depends(_automation_managers),
    db: Session = Depends(get_db),
):
    row = Automation(
        name=payload.name,
        description=payload.description,
        trigger=payload.trigger,
        conditions=json.dumps([c.model_dump() for c in payload.conditions]),
        actions=json.dumps([a.model_dump() for a in payload.actions]),
        enabled=payload.enabled,
        created_by_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    write_audit_log(
        db,
        action="automation_create",
        entity_type="automation",
        entity_id=row.id,
        user_id=current_user.id,
        description=f"Created automation '{row.name}' trigger={row.trigger.value}",
        request=request,
    )
    return _to_response(row)


@router.get("/{automation_id}", response_model=AutomationResponse)
def get_automation(
    automation_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    row = db.query(Automation).filter(Automation.id == automation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    return _to_response(row)


@router.put("/{automation_id}", response_model=AutomationResponse)
def update_automation(
    automation_id: int,
    payload: AutomationUpdate,
    request: Request,
    current_user: User = Depends(_automation_managers),
    db: Session = Depends(get_db),
):
    row = db.query(Automation).filter(Automation.id == automation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")

    data = payload.model_dump(exclude_unset=True)
    if "conditions" in data and data["conditions"] is not None:
        data["conditions"] = json.dumps(
            [c if isinstance(c, dict) else c.model_dump() for c in data["conditions"]]
        )
    if "actions" in data and data["actions"] is not None:
        data["actions"] = json.dumps(
            [a if isinstance(a, dict) else a.model_dump() for a in data["actions"]]
        )

    for k, v in data.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)

    write_audit_log(
        db,
        action="automation_update",
        entity_type="automation",
        entity_id=row.id,
        user_id=current_user.id,
        description=f"Updated automation '{row.name}'",
        request=request,
    )
    return _to_response(row)


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_automation(
    automation_id: int,
    request: Request,
    current_user: User = Depends(_automation_managers),
    db: Session = Depends(get_db),
):
    row = db.query(Automation).filter(Automation.id == automation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    db.delete(row)
    db.commit()
    write_audit_log(
        db,
        action="automation_delete",
        entity_type="automation",
        entity_id=automation_id,
        user_id=current_user.id,
        description=f"Deleted automation id={automation_id}",
        request=request,
    )
    return None


@router.post("/{automation_id}/test", response_model=AutomationTestResult)
def test_automation(
    automation_id: int,
    payload: AutomationTestRequest,
    current_user: User = Depends(_automation_managers),
    db: Session = Depends(get_db),
):
    """Manually fire an automation against a synthetic context.

    Useful for verifying conditions / templating without waiting for a real
    domain event. The actions execute for real (a notification really lands
    in someone's inbox) so use with care.
    """
    row = db.query(Automation).filter(Automation.id == automation_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Automation not found")
    report = run_automation(db, row, payload.context)
    return AutomationTestResult(
        matched=bool(report.get("matched")),
        actions_executed=int(report.get("actions_executed", 0)),
        errors=list(report.get("errors", [])),
    )
