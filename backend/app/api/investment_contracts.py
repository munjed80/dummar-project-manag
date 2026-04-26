"""Investment Contracts CRUD endpoints.

Permission model (per spec):
- project_director: full access
- contracts_manager: full CRUD + attachment upload/manage
- investment_manager: create/view/edit (and delete) investment contracts
- property_manager: read-only (view linked contracts)
- field_team / contractor_user / citizen: 403

Expiry alerts: ``GET /investment-contracts/expiring`` returns contracts
whose end_date falls within 30/60/90 days, plus already-expired entries.
The list/detail responses also annotate ``days_until_expiry`` and a
discrete ``expiry_alert`` bucket so the frontend can highlight rows.
"""
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.database import get_db
from app.models.investment_contract import (
    InvestmentContract,
    InvestmentContractStatus,
    InvestmentType,
)
from app.models.investment_property import InvestmentProperty
from app.models.user import User, UserRole
from app.schemas.investment_contract import (
    InvestmentContractCreate,
    InvestmentContractResponse,
    InvestmentContractUpdate,
    PaginatedInvestmentContracts,
)
from app.schemas.file_utils import serialize_file_list, parse_file_list
from app.services.audit import write_audit_log


router = APIRouter(prefix="/investment-contracts", tags=["investment-contracts"])


# Roles that can create/edit/delete investment contracts.
_contract_managers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
    UserRole.INVESTMENT_MANAGER,
)

# Roles that can read contracts (managers + property_manager view).
_contract_viewers = require_role(
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
    UserRole.INVESTMENT_MANAGER,
    UserRole.PROPERTY_MANAGER,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Boundaries for the discrete expiry-alert bucket the frontend renders.
ALERT_DAYS = (30, 60, 90)


def _expiry_bucket(end_date: date, today: Optional[date] = None) -> tuple[int, Optional[str]]:
    """Return (days_until_expiry, alert_bucket) for a given end_date.

    days_until_expiry can be negative for already-expired contracts.
    alert_bucket is "expired", "30", "60", "90", or None.
    """
    today = today or date.today()
    delta = (end_date - today).days
    if delta < 0:
        return delta, "expired"
    for boundary in ALERT_DAYS:
        if delta <= boundary:
            return delta, str(boundary)
    return delta, None


def _serialize_contract(c: InvestmentContract) -> InvestmentContractResponse:
    """Build the response model with computed expiry fields."""
    days, bucket = _expiry_bucket(c.end_date)
    payload = InvestmentContractResponse.model_validate(c)
    payload.days_until_expiry = days
    payload.expiry_alert = bucket
    return payload


def _ensure_property_exists(db: Session, property_id: int) -> InvestmentProperty:
    prop = (
        db.query(InvestmentProperty)
        .filter(InvestmentProperty.id == property_id)
        .first()
    )
    if not prop or not prop.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linked property not found or inactive",
        )
    return prop


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=InvestmentContractResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_investment_contract(
    payload: InvestmentContractCreate,
    request: Request,
    current_user: User = Depends(_contract_managers),
    db: Session = Depends(get_db),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )

    _ensure_property_exists(db, payload.property_id)

    if (
        db.query(InvestmentContract)
        .filter(InvestmentContract.contract_number == payload.contract_number)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract number already exists",
        )

    data = payload.model_dump()
    data["additional_attachments"] = serialize_file_list(
        data.get("additional_attachments")
    )
    data["handover_property_images"] = serialize_file_list(
        data.get("handover_property_images")
    )
    data["financial_documents"] = serialize_file_list(
        data.get("financial_documents")
    )

    contract = InvestmentContract(
        **data,
        created_by_id=current_user.id,
        status=InvestmentContractStatus.ACTIVE,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    write_audit_log(
        db,
        action="investment_contract_create",
        entity_type="investment_contract",
        entity_id=contract.id,
        user_id=current_user.id,
        description=(
            f"Investment contract {contract.contract_number} for property "
            f"{contract.property_id} created"
        ),
        request=request,
    )

    return _serialize_contract(contract)


@router.get("/", response_model=PaginatedInvestmentContracts)
def list_investment_contracts(
    skip: int = 0,
    limit: int = 100,
    property_id: Optional[int] = None,
    investor: Optional[str] = None,
    status_filter: Optional[InvestmentContractStatus] = None,
    end_date_before: Optional[date] = None,
    q: Optional[str] = None,
    current_user: User = Depends(_contract_viewers),
    db: Session = Depends(get_db),
):
    query = db.query(InvestmentContract).filter(InvestmentContract.is_active == True)

    if property_id is not None:
        query = query.filter(InvestmentContract.property_id == property_id)
    if investor:
        query = query.filter(InvestmentContract.investor_name.ilike(f"%{investor}%"))
    if status_filter is not None:
        query = query.filter(InvestmentContract.status == status_filter)
    if end_date_before is not None:
        query = query.filter(InvestmentContract.end_date <= end_date_before)
    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                InvestmentContract.contract_number.ilike(term),
                InvestmentContract.investor_name.ilike(term),
                InvestmentContract.notes.ilike(term),
            )
        )

    total_count = query.count()
    items = (
        query.order_by(InvestmentContract.end_date.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return PaginatedInvestmentContracts(
        total_count=total_count,
        items=[_serialize_contract(c) for c in items],
    )


@router.get("/expiring", response_model=List[InvestmentContractResponse])
def list_expiring_contracts(
    within_days: int = 90,
    include_expired: bool = True,
    current_user: User = Depends(_contract_viewers),
    db: Session = Depends(get_db),
):
    """Return active contracts ending within ``within_days`` (default 90)
    plus optionally already-expired contracts."""
    today = date.today()
    cutoff = today + timedelta(days=within_days)

    query = db.query(InvestmentContract).filter(
        InvestmentContract.is_active == True,
        InvestmentContract.status != InvestmentContractStatus.CANCELLED,
    )
    if include_expired:
        query = query.filter(InvestmentContract.end_date <= cutoff)
    else:
        query = query.filter(
            InvestmentContract.end_date <= cutoff,
            InvestmentContract.end_date >= today,
        )

    rows = query.order_by(InvestmentContract.end_date.asc()).all()
    return [_serialize_contract(c) for c in rows]


@router.get("/{contract_id}", response_model=InvestmentContractResponse)
def get_investment_contract(
    contract_id: int,
    current_user: User = Depends(_contract_viewers),
    db: Session = Depends(get_db),
):
    contract = (
        db.query(InvestmentContract)
        .filter(InvestmentContract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Investment contract not found")
    return _serialize_contract(contract)


@router.put("/{contract_id}", response_model=InvestmentContractResponse)
def update_investment_contract(
    contract_id: int,
    payload: InvestmentContractUpdate,
    request: Request,
    current_user: User = Depends(_contract_managers),
    db: Session = Depends(get_db),
):
    contract = (
        db.query(InvestmentContract)
        .filter(InvestmentContract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Investment contract not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "property_id" in update_data and update_data["property_id"] != contract.property_id:
        _ensure_property_exists(db, update_data["property_id"])

    if "contract_number" in update_data and update_data["contract_number"] != contract.contract_number:
        existing = (
            db.query(InvestmentContract)
            .filter(
                InvestmentContract.contract_number == update_data["contract_number"],
                InvestmentContract.id != contract.id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contract number already exists",
            )

    new_start = update_data.get("start_date", contract.start_date)
    new_end = update_data.get("end_date", contract.end_date)
    if new_end < new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )

    if "additional_attachments" in update_data:
        update_data["additional_attachments"] = serialize_file_list(
            update_data["additional_attachments"]
        )
    if "handover_property_images" in update_data:
        update_data["handover_property_images"] = serialize_file_list(
            update_data["handover_property_images"]
        )
    if "financial_documents" in update_data:
        update_data["financial_documents"] = serialize_file_list(
            update_data["financial_documents"]
        )

    for field, value in update_data.items():
        setattr(contract, field, value)

    db.commit()
    db.refresh(contract)

    write_audit_log(
        db,
        action="investment_contract_update",
        entity_type="investment_contract",
        entity_id=contract.id,
        user_id=current_user.id,
        description=f"Investment contract {contract.contract_number} updated",
        request=request,
    )

    return _serialize_contract(contract)


@router.delete("/{contract_id}")
def delete_investment_contract(
    contract_id: int,
    request: Request,
    current_user: User = Depends(_contract_managers),
    db: Session = Depends(get_db),
):
    contract = (
        db.query(InvestmentContract)
        .filter(InvestmentContract.id == contract_id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Investment contract not found")

    contract.is_active = False
    contract.status = InvestmentContractStatus.CANCELLED
    db.commit()

    write_audit_log(
        db,
        action="investment_contract_delete",
        entity_type="investment_contract",
        entity_id=contract.id,
        user_id=current_user.id,
        description=(
            f"Investment contract {contract.contract_number} cancelled/deactivated"
        ),
        request=request,
    )

    return {"message": "Investment contract cancelled successfully"}
