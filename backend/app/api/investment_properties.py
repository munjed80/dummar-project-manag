from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db
from app.models.investment_property import InvestmentProperty, PropertyType, PropertyStatus
from app.models.user import User, UserRole
from app.schemas.investment_property import (
    InvestmentPropertyCreate,
    InvestmentPropertyUpdate,
    InvestmentPropertyResponse,
    PaginatedInvestmentProperties,
)
from app.api.deps import get_current_internal_user, require_role
from app.services.audit import write_audit_log

router = APIRouter(prefix="/investment-properties", tags=["investment-properties"])

_property_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
)


@router.post("/", response_model=InvestmentPropertyResponse, status_code=status.HTTP_201_CREATED)
def create_investment_property(
    prop: InvestmentPropertyCreate,
    request: Request,
    current_user: User = Depends(_property_managers),
    db: Session = Depends(get_db),
):
    db_prop = InvestmentProperty(
        **prop.model_dump(),
        created_by_id=current_user.id,
    )
    db.add(db_prop)
    db.commit()
    db.refresh(db_prop)

    write_audit_log(
        db,
        action="investment_property_create",
        entity_type="investment_property",
        entity_id=db_prop.id,
        user_id=current_user.id,
        description=f"Investment property '{db_prop.address}' created",
        request=request,
    )

    return db_prop


@router.get("/", response_model=PaginatedInvestmentProperties)
def list_investment_properties(
    skip: int = 0,
    limit: int = 100,
    type: Optional[PropertyType] = None,
    status: Optional[PropertyStatus] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    query = db.query(InvestmentProperty).filter(InvestmentProperty.is_active == True)

    if type:
        query = query.filter(InvestmentProperty.property_type == type)

    if status:
        query = query.filter(InvestmentProperty.status == status)

    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                InvestmentProperty.address.ilike(search_term),
                InvestmentProperty.owner_name.ilike(search_term),
                InvestmentProperty.description.ilike(search_term),
            )
        )

    total_count = query.count()
    items = query.order_by(InvestmentProperty.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedInvestmentProperties(total_count=total_count, items=items)


@router.get("/{property_id}", response_model=InvestmentPropertyResponse)
def get_investment_property(
    property_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    prop = db.query(InvestmentProperty).filter(InvestmentProperty.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Investment property not found")
    return prop


@router.put("/{property_id}", response_model=InvestmentPropertyResponse)
def update_investment_property(
    property_id: int,
    prop_update: InvestmentPropertyUpdate,
    request: Request,
    current_user: User = Depends(_property_managers),
    db: Session = Depends(get_db),
):
    prop = db.query(InvestmentProperty).filter(InvestmentProperty.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Investment property not found")

    update_data = prop_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prop, field, value)

    db.commit()
    db.refresh(prop)

    write_audit_log(
        db,
        action="investment_property_update",
        entity_type="investment_property",
        entity_id=prop.id,
        user_id=current_user.id,
        description=f"Investment property '{prop.address}' updated",
        request=request,
    )

    return prop


@router.delete("/{property_id}")
def delete_investment_property(
    property_id: int,
    request: Request,
    current_user: User = Depends(_property_managers),
    db: Session = Depends(get_db),
):
    prop = db.query(InvestmentProperty).filter(InvestmentProperty.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Investment property not found")

    write_audit_log(
        db,
        action="investment_property_delete",
        entity_type="investment_property",
        entity_id=prop.id,
        user_id=current_user.id,
        description=f"Investment property '{prop.address}' deactivated",
        request=request,
    )

    prop.is_active = False
    db.commit()

    return {"message": "Investment property deleted successfully"}
