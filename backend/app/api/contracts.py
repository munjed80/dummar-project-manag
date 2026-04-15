from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from app.core.database import get_db
from app.models.contract import Contract, ContractApproval, ContractStatus
from app.models.user import User
from app.schemas.contract import (
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractApprovalRequest,
    ContractApprovalResponse,
)
from app.api.deps import get_current_user, get_current_contracts_manager
from app.services.audit import write_audit_log
import qrcode
import io
import base64

router = APIRouter(prefix="/contracts", tags=["contracts"])


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
    
    write_audit_log(db, action="contract_create", entity_type="contract", entity_id=db_contract.id, user_id=current_user.id, description=f"Contract {db_contract.contract_number} created")
    
    return db_contract


@router.get("/", response_model=List[ContractResponse])
def list_contracts(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[ContractStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Contract)
    
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    
    contracts = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()
    return contracts


@router.get("/expiring-soon", response_model=List[ContractResponse])
def get_expiring_contracts(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from datetime import date
    threshold_date = date.today() + timedelta(days=days)
    
    contracts = db.query(Contract).filter(
        Contract.status == ContractStatus.ACTIVE,
        Contract.end_date <= threshold_date,
        Contract.end_date >= date.today()
    ).all()
    
    return contracts


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.put("/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: int,
    contract_update: ContractUpdate,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    update_data = contract_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contract, field, value)
    
    db.commit()
    db.refresh(contract)
    
    write_audit_log(db, action="contract_update", entity_type="contract", entity_id=contract.id, user_id=current_user.id, description=f"Contract {contract.contract_number} updated")
    
    return contract


@router.post("/{contract_id}/approve", response_model=ContractResponse)
def approve_contract(
    contract_id: int,
    approval_request: ContractApprovalRequest,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if approval_request.action == "approve":
        contract.status = ContractStatus.APPROVED
        contract.approved_by_id = current_user.id
        contract.approved_at = datetime.utcnow()
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
    
    write_audit_log(db, action=f"contract_{approval_request.action}", entity_type="contract", entity_id=contract.id, user_id=current_user.id, description=f"Contract {contract.contract_number} - action: {approval_request.action}")
    
    return contract


@router.post("/{contract_id}/generate-pdf")
def generate_contract_pdf_endpoint(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    from app.services.pdf_generator import generate_contract_pdf
    pdf_path = generate_contract_pdf(contract)
    contract.pdf_file = pdf_path
    db.commit()

    return {"pdf_path": pdf_path}


@router.get("/{contract_id}/approvals", response_model=List[ContractApprovalResponse])
def get_contract_approvals(
    contract_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    approvals = db.query(ContractApproval).filter(
        ContractApproval.contract_id == contract_id
    ).order_by(ContractApproval.created_at.desc()).all()
    
    return approvals


@router.delete("/{contract_id}")
def delete_contract(
    contract_id: int,
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
    
    write_audit_log(db, action="contract_delete", entity_type="contract", entity_id=contract.id, user_id=current_user.id, description=f"Contract {contract.contract_number} deleted")
    
    db.delete(contract)
    db.commit()
    
    return {"message": "Contract deleted successfully"}
