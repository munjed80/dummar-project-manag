"""Violations API — independent module mounted at /violations.

Authorization is enforced through the existing fine-grained ``permissions``
core (RBAC + organization scope), not a per-route role list. The
organization scope is taken from the ``district_id`` (preferred) or
``municipality_id`` field on each violation, denormalized into the existing
``org_unit_id`` column so the standard ``scope_query`` helper works
unchanged.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_internal_user, get_current_user, require_role
from app.core import permissions as perms
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.violation import (
    Violation,
    ViolationSeverity,
    ViolationStatus,
    ViolationType,
)
from app.schemas.violation import (
    ViolationCreate,
    ViolationListResponse,
    ViolationRead,
    ViolationStatusUpdate,
    ViolationUpdate,
)
from app.services.audit import write_audit_log


router = APIRouter(prefix="/violations", tags=["violations"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_violation_number(db: Session) -> str:
    """Return a unique human-readable identifier like VIO-2026-0001.

    The numeric suffix counts existing rows for the current calendar year.
    A defensive uniqueness check then falls back to a UUID-derived suffix
    on the (rare) race where two concurrent inserts would collide. The
    underlying column also carries a UNIQUE constraint, so any remaining
    race is caught by the database.
    """
    year = datetime.now(timezone.utc).year
    prefix = f"VIO-{year}-"
    count = (
        db.query(Violation)
        .filter(Violation.violation_number.like(f"{prefix}%"))
        .count()
    )
    candidate = f"{prefix}{count + 1:04d}"
    if db.query(Violation).filter(Violation.violation_number == candidate).first():
        # UUID-derived fallback: 8 hex chars ⇒ 16M-space, collision-free for
        # all realistic concurrency.
        candidate = f"{prefix}{uuid.uuid4().hex[:8]}"
    return candidate


def _resolve_org_unit_id(
    municipality_id: Optional[int], district_id: Optional[int]
) -> Optional[int]:
    """Pick the most-specific org unit available for RBAC scoping."""
    return district_id if district_id is not None else municipality_id


def _ensure_can(
    db: Session,
    user: User,
    action: perms.Action,
    *,
    resource: Optional[Violation] = None,
    org_unit_id: Optional[int] = None,
) -> None:
    if not perms.authorize(
        db,
        user,
        action,
        perms.ResourceType.VIOLATION,
        resource=resource,
        org_unit_id=org_unit_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access denied for action={action.value} resource=violation"
            ),
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=ViolationListResponse)
@router.get("/", response_model=ViolationListResponse)
def list_violations(
    status_filter: Optional[ViolationStatus] = Query(default=None, alias="status"),
    violation_type: Optional[ViolationType] = None,
    severity: Optional[ViolationSeverity] = None,
    municipality_id: Optional[int] = None,
    district_id: Optional[int] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_internal_user),
):
    _ensure_can(db, current_user, perms.Action.READ)

    query = db.query(Violation).filter(Violation.is_active.is_(True))

    if status_filter is not None:
        query = query.filter(Violation.status == status_filter)
    if violation_type is not None:
        query = query.filter(Violation.violation_type == violation_type)
    if severity is not None:
        query = query.filter(Violation.severity == severity)
    if municipality_id is not None:
        query = query.filter(Violation.municipality_id == municipality_id)
    if district_id is not None:
        query = query.filter(Violation.district_id == district_id)
    if q:
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Violation.title.ilike(search_term),
                Violation.description.ilike(search_term),
                Violation.violation_number.ilike(search_term),
                Violation.location_text.ilike(search_term),
                Violation.legal_reference.ilike(search_term),
            )
        )

    # Apply org-scope filter (no-op for users with global scope).
    query = perms.scope_query(query, db, current_user, Violation, org_attr="org_unit_id")

    total_count = query.count()
    items = (
        query.order_by(Violation.created_at.desc(), Violation.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ViolationListResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.post("", response_model=ViolationRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ViolationRead, status_code=status.HTTP_201_CREATED)
def create_violation(
    payload: ViolationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_unit_id = _resolve_org_unit_id(payload.municipality_id, payload.district_id)
    _ensure_can(db, current_user, perms.Action.CREATE, org_unit_id=org_unit_id)

    data = payload.model_dump()
    violation = Violation(
        violation_number=_generate_violation_number(db),
        reported_by_user_id=current_user.id,
        org_unit_id=org_unit_id,
        **data,
    )
    db.add(violation)
    db.commit()
    db.refresh(violation)

    write_audit_log(
        db,
        action="violation_create",
        entity_type="violation",
        entity_id=violation.id,
        user_id=current_user.id,
        description=(
            f"Violation '{violation.violation_number}' created "
            f"(type={violation.violation_type.value}, severity={violation.severity.value})"
        ),
        request=request,
    )

    return violation


def _get_or_404(db: Session, violation_id: int) -> Violation:
    violation = (
        db.query(Violation)
        .filter(Violation.id == violation_id, Violation.is_active.is_(True))
        .first()
    )
    if violation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")
    return violation


@router.get("/{violation_id}", response_model=ViolationRead)
def get_violation(
    violation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_internal_user),
):
    violation = _get_or_404(db, violation_id)
    _ensure_can(db, current_user, perms.Action.READ, resource=violation)
    return violation


@router.patch("/{violation_id}", response_model=ViolationRead)
def update_violation(
    violation_id: int,
    payload: ViolationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    violation = _get_or_404(db, violation_id)
    _ensure_can(db, current_user, perms.Action.UPDATE, resource=violation)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(violation, field, value)

    # Re-derive org_unit_id when municipality/district was modified, so RBAC
    # scoping continues to reflect the most-specific known unit.
    if "municipality_id" in update_data or "district_id" in update_data:
        violation.org_unit_id = _resolve_org_unit_id(
            violation.municipality_id, violation.district_id
        )

    # Track resolved_at automatically when the status flips to RESOLVED.
    if update_data.get("status") == ViolationStatus.RESOLVED and violation.resolved_at is None:
        violation.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(violation)

    write_audit_log(
        db,
        action="violation_update",
        entity_type="violation",
        entity_id=violation.id,
        user_id=current_user.id,
        description=f"Violation '{violation.violation_number}' updated",
        request=request,
    )

    return violation


@router.patch("/{violation_id}/status", response_model=ViolationRead)
def update_violation_status(
    violation_id: int,
    payload: ViolationStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    violation = _get_or_404(db, violation_id)
    _ensure_can(db, current_user, perms.Action.UPDATE, resource=violation)

    old_status = violation.status
    violation.status = payload.status
    if payload.status == ViolationStatus.RESOLVED and violation.resolved_at is None:
        violation.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(violation)

    description = (
        f"Violation '{violation.violation_number}' status: "
        f"{old_status.value} → {payload.status.value}"
    )
    if payload.note:
        description += f" — {payload.note}"

    write_audit_log(
        db,
        action="violation_status_update",
        entity_type="violation",
        entity_id=violation.id,
        user_id=current_user.id,
        description=description,
        request=request,
    )

    return violation


# Soft-delete is restricted to PROJECT_DIRECTOR. The same role check is
# layered on top of the permission matrix, matching the deletion pattern
# used by other modules.
_violation_deleter = require_role(UserRole.PROJECT_DIRECTOR)


@router.delete("/{violation_id}")
def delete_violation(
    violation_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(_violation_deleter),
):
    violation = _get_or_404(db, violation_id)
    _ensure_can(db, current_user, perms.Action.DELETE, resource=violation)

    write_audit_log(
        db,
        action="violation_delete",
        entity_type="violation",
        entity_id=violation.id,
        user_id=current_user.id,
        description=f"Violation '{violation.violation_number}' deactivated",
        request=request,
    )

    violation.is_active = False
    db.commit()

    return {"message": "Violation deleted successfully", "id": violation_id}
