"""CRUD endpoints for OrganizationUnit (administrative hierarchy).

Restricted to PROJECT_DIRECTOR. The hierarchy invariant — a unit's level must
be exactly one step deeper than its parent — is enforced here as well as in
the service layer. The /tree endpoint returns the full hierarchy in a single
round-trip for the frontend org-picker.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_director, get_current_internal_user
from app.core.database import get_db
from app.models.organization import OrgLevel, OrganizationUnit, expected_child_level
from app.models.user import User
from app.schemas.organization import (
    OrganizationUnitCreate,
    OrganizationUnitResponse,
    OrganizationUnitTreeNode,
    OrganizationUnitUpdate,
)

router = APIRouter(prefix="/organization-units", tags=["organization-units"])


def _validate_hierarchy(
    db: Session, level: OrgLevel, parent_id: Optional[int]
) -> None:
    if parent_id is None:
        if level != OrgLevel.GOVERNORATE:
            raise HTTPException(
                status_code=400,
                detail="Only governorate units may have no parent",
            )
        return
    parent = (
        db.query(OrganizationUnit).filter(OrganizationUnit.id == parent_id).first()
    )
    if parent is None:
        raise HTTPException(status_code=400, detail="Parent unit not found")
    expected = expected_child_level(parent.level)
    if expected is None:
        raise HTTPException(
            status_code=400,
            detail=f"Parent level {parent.level.value} cannot have children",
        )
    if level != expected:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Child level must be {expected.value} when parent is "
                f"{parent.level.value} (got {level.value})"
            ),
        )


@router.post(
    "/", response_model=OrganizationUnitResponse, status_code=status.HTTP_201_CREATED
)
def create_unit(
    payload: OrganizationUnitCreate,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db),
):
    if (
        db.query(OrganizationUnit)
        .filter(OrganizationUnit.code == payload.code)
        .first()
    ):
        raise HTTPException(status_code=400, detail="code already exists")
    _validate_hierarchy(db, payload.level, payload.parent_id)
    unit = OrganizationUnit(
        name=payload.name,
        code=payload.code,
        level=payload.level,
        parent_id=payload.parent_id,
        is_active=payload.is_active,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/", response_model=List[OrganizationUnitResponse])
def list_units(
    level: Optional[OrgLevel] = None,
    parent_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = db.query(OrganizationUnit)
    if level is not None:
        query = query.filter(OrganizationUnit.level == level)
    if parent_id is not None:
        query = query.filter(OrganizationUnit.parent_id == parent_id)
    return query.order_by(OrganizationUnit.level, OrganizationUnit.name).all()


@router.get("/tree", response_model=List[OrganizationUnitTreeNode])
def get_tree(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    units = db.query(OrganizationUnit).all()
    by_id = {
        u.id: OrganizationUnitTreeNode(
            id=u.id,
            name=u.name,
            code=u.code,
            level=u.level,
            parent_id=u.parent_id,
            is_active=bool(u.is_active),
            created_at=u.created_at,
            updated_at=u.updated_at,
            children=[],
        )
        for u in units
    }
    roots: List[OrganizationUnitTreeNode] = []
    for u in units:
        node = by_id[u.id]
        if u.parent_id and u.parent_id in by_id:
            by_id[u.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


@router.get("/{unit_id}", response_model=OrganizationUnitResponse)
def get_unit(
    unit_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    unit = (
        db.query(OrganizationUnit).filter(OrganizationUnit.id == unit_id).first()
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.put("/{unit_id}", response_model=OrganizationUnitResponse)
def update_unit(
    unit_id: int,
    payload: OrganizationUnitUpdate,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db),
):
    unit = (
        db.query(OrganizationUnit).filter(OrganizationUnit.id == unit_id).first()
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    data = payload.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != unit.code:
        if (
            db.query(OrganizationUnit)
            .filter(OrganizationUnit.code == data["code"])
            .first()
        ):
            raise HTTPException(status_code=400, detail="code already exists")
    if "parent_id" in data:
        new_parent = data["parent_id"]
        if new_parent == unit.id:
            raise HTTPException(status_code=400, detail="Unit cannot be its own parent")
        _validate_hierarchy(db, unit.level, new_parent)
    for k, v in data.items():
        setattr(unit, k, v)
    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/{unit_id}")
def delete_unit(
    unit_id: int,
    current_user: User = Depends(get_current_active_director),
    db: Session = Depends(get_db),
):
    unit = (
        db.query(OrganizationUnit).filter(OrganizationUnit.id == unit_id).first()
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    has_children = (
        db.query(OrganizationUnit)
        .filter(OrganizationUnit.parent_id == unit.id)
        .first()
    )
    if has_children:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a unit that still has children",
        )
    unit.is_active = False
    db.commit()
    return {"message": "Unit deactivated", "id": unit.id}
