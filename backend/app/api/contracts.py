from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import json
import logging
from app.core.database import get_db
from app.models.contract import Contract, ContractApproval, ContractStatus, ContractType
from app.models.user import User, UserRole
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractApprovalRequest,
    ContractApprovalResponse,
)
from app.schemas.report import PaginatedContracts
from app.api.deps import get_current_user, get_current_contracts_manager, get_current_internal_user
from app.core import permissions as perms
from app.services.audit import write_audit_log
from app.services.pdf_generator import generate_contract_pdf
from app.services.notification_service import notify_contract_status_change
import qrcode
import io
import base64

router = APIRouter(prefix="/contracts", tags=["contracts"])
logger = logging.getLogger("dummar.contracts")


def _apply_contract_read_scope(query, current_user: User):
    # Field teams and contractor users cannot browse operational contracts
    # unless they own/created the record.
    if current_user.role in (UserRole.FIELD_TEAM, UserRole.CONTRACTOR_USER):
        return query.filter(Contract.created_by_id == current_user.id)
    return query


def generate_qr_code(contract_id: int) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"https://dummar.gov.sy/contracts/verify/{contract_id}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


@router.post("/", response_model=ContractResponse)
def create_contract(
    contract: ContractCreate,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db)
):
    existing = db.query(Contract).filter(Contract.contract_number == contract.contract_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract number already exists",
        )
    
    db_contract = Contract(
        **contract.model_dump(),
        created_by_id=current_user.id,
        status=ContractStatus.DRAFT,
    )
    if db_contract.org_unit_id is None and current_user.org_unit_id is not None:
        db_contract.org_unit_id = current_user.org_unit_id
    
    db.add(db_contract)
    db.commit()
    db.refresh(db_contract)
    
    qr_code = generate_qr_code(db_contract.id)
    db_contract.qr_code = qr_code
    db.commit()
    db.refresh(db_contract)
    
    approval = ContractApproval(
        contract_id=db_contract.id,
        user_id=current_user.id,
        action="created",
        comments="Contract created",
    )
    db.add(approval)
    db.commit()
    
    write_audit_log(db, action="contract_create", entity_type="contract", entity_id=db_contract.id, user_id=current_user.id, description=f"Contract {db_contract.contract_number} created", request=request)
    
    return db_contract


@router.get("/", response_model=PaginatedContracts)
def list_contracts(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[ContractStatus] = None,
    contract_type: Optional[ContractType] = None,
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    query = db.query(Contract)
    query = perms.scope_query(query, db, current_user, Contract)
    query = _apply_contract_read_scope(query, current_user)

    if status_filter:
        query = query.filter(Contract.status == status_filter)

    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)

    if project_id:
        query = query.filter(Contract.project_id == project_id)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Contract.contract_number.ilike(search_term),
                Contract.title.ilike(search_term),
                Contract.contractor_name.ilike(search_term),
            )
        )
    
    total_count = query.count()
    contracts = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()
    return {"total_count": total_count, "items": contracts}


@router.get("/expiring-soon", response_model=List[ContractResponse])
def get_expiring_contracts(
    days: int = 30,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    from datetime import date
    threshold_date = date.today() + timedelta(days=days)
    
    query = db.query(Contract).filter(
        Contract.status == ContractStatus.ACTIVE,
        Contract.end_date <= threshold_date,
        Contract.end_date >= date.today()
    )
    query = perms.scope_query(query, db, current_user, Contract)
    query = _apply_contract_read_scope(query, current_user)

    return query.all()


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not perms.authorize(
        db, current_user, perms.Action.READ, perms.ResourceType.CONTRACT, resource=contract
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    if current_user.role in (UserRole.FIELD_TEAM, UserRole.CONTRACTOR_USER) and contract.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied for this contract")
    return contract


@router.put("/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: int,
    contract_update: ContractUpdate,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not perms.authorize(
        db, current_user, perms.Action.UPDATE, perms.ResourceType.CONTRACT, resource=contract
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    
    update_data = contract_update.model_dump(exclude_unset=True)

    # Serialize file list fields to JSON for DB storage
    if "attachments" in update_data and update_data["attachments"] is not None:
        update_data["attachments"] = json.dumps(update_data["attachments"])

    for field, value in update_data.items():
        setattr(contract, field, value)
    
    db.commit()
    db.refresh(contract)
    
    write_audit_log(db, action="contract_update", entity_type="contract", entity_id=contract.id, user_id=current_user.id, description=f"Contract {contract.contract_number} updated", request=request)
    
    return contract


@router.post("/{contract_id}/approve", response_model=ContractResponse)
def approve_contract(
    contract_id: int,
    approval_request: ContractApprovalRequest,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not perms.authorize(
        db, current_user, perms.Action.APPROVE, perms.ResourceType.CONTRACT, resource=contract
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")
    
    if approval_request.action == "approve":
        contract.status = ContractStatus.APPROVED
        contract.approved_by_id = current_user.id
        contract.approved_at = datetime.now(timezone.utc)
    elif approval_request.action == "activate":
        contract.status = ContractStatus.ACTIVE
    elif approval_request.action == "complete":
        contract.status = ContractStatus.COMPLETED
    elif approval_request.action == "suspend":
        contract.status = ContractStatus.SUSPENDED
    elif approval_request.action == "cancel":
        contract.status = ContractStatus.CANCELLED
    
    db.commit()
    db.refresh(contract)
    
    approval = ContractApproval(
        contract_id=contract.id,
        user_id=current_user.id,
        action=approval_request.action,
        comments=approval_request.comments,
    )
    db.add(approval)
    db.commit()
    
    write_audit_log(db, action=f"contract_{approval_request.action}", entity_type="contract", entity_id=contract.id, user_id=current_user.id, description=f"Contract {contract.contract_number} - action: {approval_request.action}", request=request)

    # Send notifications for contract status changes
    try:
        notify_contract_status_change(
            db=db,
            contract_id=contract.id,
            contract_number=contract.contract_number,
            action=approval_request.action,
        )
    except Exception:
        logger.exception("Notification failed for contract %s action=%s", contract.contract_number, approval_request.action)
    
    return contract


@router.post("/{contract_id}/generate-pdf")
def generate_contract_pdf_endpoint(
    contract_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    """Generate the PDF summary for a contract.

    The actual PDF rendering runs as a Celery task. When the broker is
    configured (production) the endpoint enqueues the task and returns
    ``{"job_id": ..., "status": "queued"}`` so the client can poll
    ``GET /jobs/{job_id}``. In eager mode (tests / local dev without Redis)
    the task runs inline and the response also includes ``pdf_path`` so the
    pre-existing API contract is preserved.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role in (UserRole.FIELD_TEAM, UserRole.CONTRACTOR_USER) and contract.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied for this contract")
    if not perms.authorize(
        db, current_user, perms.Action.EXPORT, perms.ResourceType.CONTRACT, resource=contract
    ) and not perms.authorize(
        db, current_user, perms.Action.READ, perms.ResourceType.CONTRACT, resource=contract
    ):
        raise HTTPException(status_code=403, detail="Out of organization scope")

    from app.jobs import dispatch, is_eager_mode
    from app.jobs.tasks import generate_contract_pdf_task

    result = dispatch(generate_contract_pdf_task, contract.id)

    if is_eager_mode():
        # Refresh so the caller sees the updated pdf_file column.
        db.refresh(contract)
        return {
            "pdf_path": contract.pdf_file,
            "job_id": result.id,
            "status": "completed",
        }

    return {"job_id": result.id, "status": "queued"}


@router.get("/{contract_id}/approvals", response_model=List[ContractApprovalResponse])
def get_contract_approvals(
    contract_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if current_user.role in (UserRole.FIELD_TEAM, UserRole.CONTRACTOR_USER) and contract.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied for this contract")

    approvals = db.query(ContractApproval).filter(
        ContractApproval.contract_id == contract_id
    ).order_by(ContractApproval.created_at.desc()).all()
    
    return approvals


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if contract.status != ContractStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft contracts can be deleted",
        )
    
    write_audit_log(db, action="contract_delete", entity_type="contract", entity_id=contract.id, user_id=current_user.id, description=f"Contract {contract.contract_number} deleted", request=request)
    
    db.delete(contract)
    db.commit()
    
    return {"message": "Contract deleted successfully"}
