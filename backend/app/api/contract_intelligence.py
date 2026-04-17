"""
Contract Intelligence Center API.

Provides endpoints for the full contract intelligence workflow:
upload → OCR → extraction → review → save → classify → summarize →
detect duplicates → flag risks → link to contract records.

RBAC: Only internal staff (contracts_manager, project_director) can access.
"""

import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func as sql_func, String
from sqlalchemy.orm import Session

from app.api.deps import get_current_contracts_manager, get_current_internal_user
from app.core.config import settings
from app.core.database import get_db
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.contract_intelligence import (
    ContractDocument,
    ContractDuplicate,
    ContractRiskFlag,
    DocumentProcessingStatus,
    DuplicateStatus,
    RiskSeverity,
)
from app.models.user import User
from app.schemas.contract_intelligence import (
    BulkImportPreview,
    BulkImportResult,
    BulkImportRow,
    ContractDocumentResponse,
    ContractDocumentUpdate,
    ContractDuplicateResponse,
    ContractDuplicateReview,
    ContractRiskFlagResponse,
    IntelligenceDashboardStats,
    ProcessingQueueResponse,
)
from app.services.audit import write_audit_log
from app.services.classification_service import classify_contract
from app.services.duplicate_service import find_duplicates, save_duplicate_records
from app.services.extraction_service import extract_fields, fields_from_json, fields_to_json
from app.services.ocr_service import process_ocr, get_ocr_status
from app.services.risk_service import analyze_contract_risks, save_risk_flags
from app.services.summary_service import generate_summary
from app.services.notification_service import notify_intelligence_processing_complete

router = APIRouter(prefix="/contract-intelligence", tags=["contract-intelligence"])
logger = logging.getLogger("dummar.contract_intelligence")

ALLOWED_DOC_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".csv", ".xlsx", ".xls", ".txt"}
MAX_DOC_SIZE = 20 * 1024 * 1024  # 20MB
MAX_IMPORT_ROWS = 500  # Safety limit for bulk import (CSV/Excel)
BATCH_FAILURE_THRESHOLD = 0.5  # 50% — notify as batch_import_failed if failures exceed this


# ─────────────────────────────────────────────────────────────
# Dashboard & Stats
# ─────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=IntelligenceDashboardStats)
def get_intelligence_dashboard(
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Get contract intelligence dashboard statistics."""
    total = db.query(sql_func.count(ContractDocument.id)).scalar() or 0

    status_counts = {}
    for s in DocumentProcessingStatus:
        count = db.query(sql_func.count(ContractDocument.id)).filter(
            ContractDocument.processing_status == s
        ).scalar() or 0
        status_counts[s.value] = count

    total_risks = db.query(sql_func.count(ContractRiskFlag.id)).scalar() or 0
    unresolved_risks = db.query(sql_func.count(ContractRiskFlag.id)).filter(
        ContractRiskFlag.is_resolved == False
    ).scalar() or 0
    critical_risks = db.query(sql_func.count(ContractRiskFlag.id)).filter(
        ContractRiskFlag.severity == RiskSeverity.CRITICAL,
        ContractRiskFlag.is_resolved == False,
    ).scalar() or 0
    high_risks = db.query(sql_func.count(ContractRiskFlag.id)).filter(
        ContractRiskFlag.severity == RiskSeverity.HIGH,
        ContractRiskFlag.is_resolved == False,
    ).scalar() or 0

    total_dups = db.query(sql_func.count(ContractDuplicate.id)).scalar() or 0
    pending_dups = db.query(sql_func.count(ContractDuplicate.id)).filter(
        ContractDuplicate.status == DuplicateStatus.PENDING
    ).scalar() or 0

    avg_ocr = db.query(sql_func.avg(ContractDocument.ocr_confidence)).filter(
        ContractDocument.ocr_confidence.isnot(None)
    ).scalar()

    avg_ext = db.query(sql_func.avg(ContractDocument.extraction_confidence)).filter(
        ContractDocument.extraction_confidence.isnot(None)
    ).scalar()

    return IntelligenceDashboardStats(
        total_documents=total,
        queued=status_counts.get("queued", 0),
        processing=status_counts.get("processing", 0),
        ocr_complete=status_counts.get("ocr_complete", 0),
        extracted=status_counts.get("extracted", 0),
        review=status_counts.get("review", 0),
        approved=status_counts.get("approved", 0),
        rejected=status_counts.get("rejected", 0),
        failed=status_counts.get("failed", 0),
        total_risk_flags=total_risks,
        unresolved_risk_flags=unresolved_risks,
        critical_risks=critical_risks,
        high_risks=high_risks,
        total_duplicates=total_dups,
        pending_duplicates=pending_dups,
        avg_ocr_confidence=round(avg_ocr, 3) if avg_ocr is not None else None,
        avg_extraction_confidence=round(avg_ext, 3) if avg_ext is not None else None,
    )


# ─────────────────────────────────────────────────────────────
# Document Upload & Processing
# ─────────────────────────────────────────────────────────────

@router.post("/upload", response_model=ContractDocumentResponse)
async def upload_contract_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Upload a contract document for OCR processing and intelligence extraction.
    Supports PDF, images (JPG/PNG/TIFF), and text files.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نوع الملف {ext} غير مدعوم",
        )

    content = await file.read()
    if len(content) > MAX_DOC_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="حجم الملف كبير جداً (الحد الأقصى 20MB)",
        )

    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, "contract_intelligence")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    stored_path = f"/uploads/contract_intelligence/{filename}"

    # Create document record
    doc = ContractDocument(
        original_filename=file.filename or "unknown",
        stored_path=stored_path,
        file_type=ext.lstrip("."),
        file_size=len(content),
        processing_status=DocumentProcessingStatus.QUEUED,
        uploaded_by_id=current_user.id,
        import_source="upload",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    write_audit_log(
        db,
        action="contract_doc_upload",
        entity_type="contract_document",
        entity_id=doc.id,
        user_id=current_user.id,
        description=f"Uploaded contract document: {file.filename}",
        request=request,
    )

    # Auto-process the document
    _process_document(db, doc, filepath, current_user.id, request)

    db.refresh(doc)
    return doc


def _process_document(
    db: Session,
    doc: ContractDocument,
    filepath: str,
    user_id: int,
    request: Optional[Request] = None,
):
    """Run the full intelligence pipeline on a document."""
    try:
        # Step 1: OCR
        doc.processing_status = DocumentProcessingStatus.PROCESSING
        db.commit()

        ocr_result = process_ocr(filepath, doc.file_type or "")

        doc.ocr_text = ocr_result.text
        doc.ocr_confidence = ocr_result.confidence
        doc.ocr_engine = ocr_result.engine
        doc.ocr_completed_at = datetime.utcnow()

        if not ocr_result.success:
            doc.processing_status = DocumentProcessingStatus.FAILED
            doc.error_message = "; ".join(ocr_result.warnings) if ocr_result.warnings else "OCR failed"
            db.commit()
            return

        doc.processing_status = DocumentProcessingStatus.OCR_COMPLETE
        db.commit()

        # Step 2: Field extraction
        extraction_result = extract_fields(ocr_result.text)
        doc.extracted_fields = fields_to_json(extraction_result.fields)
        doc.extraction_confidence = extraction_result.confidence
        doc.extraction_notes = "; ".join(extraction_result.notes) if extraction_result.notes else None

        doc.processing_status = DocumentProcessingStatus.EXTRACTED
        db.commit()

        # Step 3: Classification
        classification = classify_contract(
            text=ocr_result.text,
            extracted_fields=extraction_result.fields,
        )
        doc.suggested_type = classification.suggested_type
        doc.classification_confidence = classification.confidence
        doc.classification_reason = classification.reason
        db.commit()

        # Step 4: Summary
        summary = generate_summary(
            extracted_fields=extraction_result.fields,
            ocr_text=ocr_result.text,
            contract_type=classification.suggested_type,
        )
        doc.auto_summary = summary
        db.commit()

        # Step 5: Risk analysis
        risk_flags = analyze_contract_risks(
            extracted_fields=extraction_result.fields,
            ocr_text=ocr_result.text,
        )
        if risk_flags:
            save_risk_flags(db, risk_flags, document_id=doc.id)

        # Step 6: Duplicate detection
        fields = extraction_result.fields
        matches = find_duplicates(
            db,
            contract_number=fields.get("contract_number"),
            contractor_name=fields.get("contractor_name"),
            title=fields.get("title"),
            contract_value=fields.get("contract_value"),
            start_date=fields.get("start_date"),
            end_date=fields.get("end_date"),
        )
        if matches:
            save_duplicate_records(db, document_id=doc.id, matches=matches)

        # Set final status
        if doc.ocr_confidence and doc.ocr_confidence < 0.3:
            doc.processing_status = DocumentProcessingStatus.REVIEW
        elif doc.extraction_confidence and doc.extraction_confidence < 0.3:
            doc.processing_status = DocumentProcessingStatus.REVIEW
        else:
            doc.processing_status = DocumentProcessingStatus.REVIEW

        db.commit()

        write_audit_log(
            db,
            action="contract_doc_processed",
            entity_type="contract_document",
            entity_id=doc.id,
            user_id=user_id,
            description=f"Document processed: OCR={doc.ocr_confidence}, extraction={doc.extraction_confidence}",
            request=request,
        )

        # Send processing-completion notifications
        try:
            notify_intelligence_processing_complete(
                db, event="extraction_review_ready",
                document_id=doc.id,
                details=f"ثقة OCR: {doc.ocr_confidence}, ثقة الاستخراج: {doc.extraction_confidence}",
            )
            # If high/critical risks found, send risk notification
            high_risk_count = sum(1 for f in risk_flags if f.get("severity") in ("high", "critical"))
            if high_risk_count > 0:
                notify_intelligence_processing_complete(
                    db, event="risk_review_needed",
                    document_id=doc.id,
                    details=f"{high_risk_count} مخاطر مرتفعة/حرجة",
                )
            # If duplicates found, notify
            if matches:
                notify_intelligence_processing_complete(
                    db, event="duplicate_review_needed",
                    document_id=doc.id,
                    details=f"{len(matches)} تكرارات محتملة",
                )
        except Exception:
            logger.exception("Notification failed for doc %s (non-fatal)", doc.id)

    except Exception as e:
        logger.exception("Document processing failed for doc %s", doc.id)
        doc.processing_status = DocumentProcessingStatus.FAILED
        doc.error_message = str(e)
        try:
            db.commit()
        except Exception:
            db.rollback()


# ─────────────────────────────────────────────────────────────
# Processing Queue
# ─────────────────────────────────────────────────────────────

@router.get("/queue", response_model=ProcessingQueueResponse)
def get_processing_queue(
    status_filter: Optional[DocumentProcessingStatus] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Get the document processing queue."""
    query = db.query(ContractDocument)

    if status_filter:
        query = query.filter(ContractDocument.processing_status == status_filter)

    total = query.count()
    docs = query.order_by(ContractDocument.created_at.desc()).offset(skip).limit(limit).all()

    return ProcessingQueueResponse(
        queue_length=total,
        documents=docs,
        status_filter=status_filter,
    )


# ─────────────────────────────────────────────────────────────
# Document Details & Review
# ─────────────────────────────────────────────────────────────

@router.get("/documents/{document_id}", response_model=ContractDocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Get a specific contract document."""
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")
    return doc


@router.put("/documents/{document_id}", response_model=ContractDocumentResponse)
def update_document(
    document_id: int,
    update: ContractDocumentUpdate,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Update a contract document (edit extracted fields, summary, etc.)."""
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")

    update_data = update.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        if value is not None:
            setattr(doc, field_name, value)

    db.commit()
    db.refresh(doc)

    write_audit_log(
        db,
        action="contract_doc_update",
        entity_type="contract_document",
        entity_id=doc.id,
        user_id=current_user.id,
        description=f"Document updated: {list(update_data.keys())}",
        request=request,
    )

    return doc


@router.post("/documents/{document_id}/approve", response_model=ContractDocumentResponse)
def approve_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Approve extracted data and mark document as approved."""
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")

    doc.processing_status = DocumentProcessingStatus.APPROVED
    doc.reviewed_by_id = current_user.id
    doc.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)

    write_audit_log(
        db,
        action="contract_doc_approve",
        entity_type="contract_document",
        entity_id=doc.id,
        user_id=current_user.id,
        description=f"Document approved: {doc.original_filename}",
        request=request,
    )

    return doc


@router.post("/documents/{document_id}/reject", response_model=ContractDocumentResponse)
def reject_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Reject a document."""
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")

    doc.processing_status = DocumentProcessingStatus.REJECTED
    doc.reviewed_by_id = current_user.id
    doc.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)

    write_audit_log(
        db,
        action="contract_doc_reject",
        entity_type="contract_document",
        entity_id=doc.id,
        user_id=current_user.id,
        description=f"Document rejected: {doc.original_filename}",
        request=request,
    )

    return doc


@router.post("/documents/{document_id}/reprocess", response_model=ContractDocumentResponse)
def reprocess_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Re-run the intelligence pipeline on a document."""
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")

    # Clear old risk flags and duplicates
    db.query(ContractRiskFlag).filter(ContractRiskFlag.document_id == doc.id).delete()
    db.query(ContractDuplicate).filter(ContractDuplicate.document_id == doc.id).delete()
    db.commit()

    # Reconstruct file path
    filepath = os.path.join(settings.UPLOAD_DIR, doc.stored_path.lstrip("/uploads/"))
    # Normalize path  
    filepath = os.path.join(settings.UPLOAD_DIR, *doc.stored_path.strip("/").split("/")[1:])

    _process_document(db, doc, filepath, current_user.id, request)

    db.refresh(doc)
    return doc


# ─────────────────────────────────────────────────────────────
# Convert to Contract
# ─────────────────────────────────────────────────────────────

@router.post("/documents/{document_id}/convert-to-contract")
def convert_to_contract(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Convert an approved document to a real contract record.
    Uses extracted fields to create the contract.
    """
    doc = db.query(ContractDocument).filter(ContractDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="المستند غير موجود")

    if doc.contract_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="المستند مرتبط بعقد بالفعل",
        )

    fields = fields_from_json(doc.extracted_fields)

    # Validate minimum required fields
    contract_number = fields.get("contract_number") or f"AUTO-{doc.id:06d}"
    title = fields.get("title") or doc.original_filename
    contractor_name = fields.get("contractor_name") or "غير محدد"
    scope = fields.get("scope_summary") or fields.get("scope_description") or "مستخرج تلقائياً"

    # Map contract type
    suggested = doc.suggested_type or fields.get("contract_type") or "other"
    type_map = {
        "maintenance": ContractType.MAINTENANCE,
        "construction": ContractType.CONSTRUCTION,
        "supply": ContractType.SUPPLY,
        "consulting": ContractType.CONSULTING,
        "cleaning": ContractType.OTHER,
        "roads": ContractType.OTHER,
        "lighting": ContractType.OTHER,
        "services": ContractType.OTHER,
    }
    contract_type = type_map.get(suggested, ContractType.OTHER)

    # Parse dates
    from datetime import date as date_type
    start_date = _parse_date(fields.get("start_date")) or date_type.today()
    end_date = _parse_date(fields.get("end_date")) or date_type.today()

    # Parse value
    try:
        contract_value = float(fields.get("contract_value", 0))
    except (ValueError, TypeError):
        contract_value = 0.0

    # Check for duplicate contract number
    existing = db.query(Contract).filter(Contract.contract_number == contract_number).first()
    if existing:
        contract_number = f"{contract_number}-{doc.id}"

    contract = Contract(
        contract_number=contract_number,
        title=title,
        contractor_name=contractor_name,
        contract_type=contract_type,
        contract_value=contract_value,
        start_date=start_date,
        end_date=end_date,
        execution_duration_days=fields.get("execution_duration_days"),
        scope_description=scope,
        related_areas=fields.get("covered_locations"),
        notes=doc.edited_summary or doc.auto_summary,
        status=ContractStatus.DRAFT,
        created_by_id=current_user.id,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    # Link document to contract
    doc.contract_id = contract.id
    doc.processing_status = DocumentProcessingStatus.APPROVED
    db.commit()

    # Run risk analysis on the new contract
    risk_flags = analyze_contract_risks(contract=contract)
    if risk_flags:
        save_risk_flags(db, risk_flags, contract_id=contract.id, document_id=doc.id)

    # Check for duplicate contracts
    matches = find_duplicates(
        db,
        contract_number=contract.contract_number,
        contractor_name=contract.contractor_name,
        title=contract.title,
        contract_value=float(contract.contract_value) if contract.contract_value else None,
        start_date=str(contract.start_date),
        end_date=str(contract.end_date),
        exclude_contract_id=contract.id,
    )
    if matches:
        save_duplicate_records(db, document_id=doc.id, matches=matches, contract_id_a=contract.id)

    write_audit_log(
        db,
        action="contract_doc_convert",
        entity_type="contract_document",
        entity_id=doc.id,
        user_id=current_user.id,
        description=f"Document converted to contract #{contract.contract_number}",
        request=request,
    )

    return {
        "message": "تم إنشاء العقد بنجاح",
        "contract_id": contract.id,
        "contract_number": contract.contract_number,
        "document_id": doc.id,
    }


def _parse_date(date_str: Optional[str]):
    """Parse a date string to date object."""
    if not date_str:
        return None
    try:
        from datetime import datetime as dt
        return dt.strptime(date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────
# Risk Flags
# ─────────────────────────────────────────────────────────────

@router.get("/risks", response_model=List[ContractRiskFlagResponse])
def get_risk_flags(
    document_id: Optional[int] = None,
    contract_id: Optional[int] = None,
    unresolved_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Get risk flags, optionally filtered."""
    query = db.query(ContractRiskFlag)

    if document_id:
        query = query.filter(ContractRiskFlag.document_id == document_id)
    if contract_id:
        query = query.filter(ContractRiskFlag.contract_id == contract_id)
    if unresolved_only:
        query = query.filter(ContractRiskFlag.is_resolved == False)

    return query.order_by(ContractRiskFlag.created_at.desc()).offset(skip).limit(limit).all()


@router.post("/risks/{risk_id}/resolve")
def resolve_risk_flag(
    risk_id: int,
    resolution_notes: Optional[str] = None,
    request: Request = None,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Mark a risk flag as resolved."""
    flag = db.query(ContractRiskFlag).filter(ContractRiskFlag.id == risk_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="مؤشر الخطر غير موجود")

    flag.is_resolved = True
    flag.resolved_by_id = current_user.id
    flag.resolved_at = datetime.utcnow()
    flag.resolution_notes = resolution_notes
    db.commit()

    write_audit_log(
        db,
        action="risk_flag_resolve",
        entity_type="contract_risk_flag",
        entity_id=flag.id,
        user_id=current_user.id,
        description=f"Risk flag resolved: {flag.risk_type}",
        request=request,
    )

    return {"message": "تم حل مؤشر الخطر"}


# ─────────────────────────────────────────────────────────────
# Duplicate Detection
# ─────────────────────────────────────────────────────────────

@router.get("/duplicates", response_model=List[ContractDuplicateResponse])
def get_duplicates(
    status_filter: Optional[DuplicateStatus] = None,
    document_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Get potential duplicates, optionally filtered."""
    query = db.query(ContractDuplicate)

    if status_filter:
        query = query.filter(ContractDuplicate.status == status_filter)
    if document_id:
        query = query.filter(ContractDuplicate.document_id == document_id)

    return query.order_by(ContractDuplicate.created_at.desc()).offset(skip).limit(limit).all()


@router.put("/duplicates/{duplicate_id}", response_model=ContractDuplicateResponse)
def review_duplicate(
    duplicate_id: int,
    review: ContractDuplicateReview,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Review a potential duplicate (mark as same / different / review later)."""
    dup = db.query(ContractDuplicate).filter(ContractDuplicate.id == duplicate_id).first()
    if not dup:
        raise HTTPException(status_code=404, detail="سجل التكرار غير موجود")

    dup.status = review.status
    dup.review_notes = review.review_notes
    dup.reviewed_by_id = current_user.id
    dup.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(dup)

    write_audit_log(
        db,
        action="duplicate_review",
        entity_type="contract_duplicate",
        entity_id=dup.id,
        user_id=current_user.id,
        description=f"Duplicate reviewed: {review.status.value}",
        request=request,
    )

    return dup


# ─────────────────────────────────────────────────────────────
# Bulk Import — CSV
# ─────────────────────────────────────────────────────────────

@router.post("/bulk-import/preview-csv", response_model=BulkImportPreview)
async def preview_csv_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Preview a CSV file for bulk import.
    Returns parsed rows with validation status.
    """
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("windows-1256")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    rows = []
    warnings = []

    # Column mapping (support Arabic and English headers)
    _COL_MAP = {
        "contract_number": ["contract_number", "رقم العقد", "contract_no", "number", "رقم"],
        "title": ["title", "العنوان", "عنوان العقد", "name"],
        "contractor_name": ["contractor_name", "المقاول", "اسم المقاول", "contractor", "الشركة"],
        "contract_type": ["contract_type", "النوع", "نوع العقد", "type"],
        "contract_value": ["contract_value", "القيمة", "قيمة العقد", "value", "amount"],
        "start_date": ["start_date", "تاريخ البدء", "start", "بداية"],
        "end_date": ["end_date", "تاريخ الانتهاء", "end", "نهاية"],
        "scope_description": ["scope_description", "النطاق", "نطاق العمل", "scope", "الوصف"],
    }

    if reader.fieldnames:
        # Check if we can map columns
        available = set(reader.fieldnames)
        for target, aliases in _COL_MAP.items():
            matched = any(a in available for a in aliases)
            if not matched and target in ("contract_number", "title"):
                warnings.append(f"عمود '{target}' لم يتم العثور عليه في الملف")

    for i, row in enumerate(reader, start=1):
        if i > MAX_IMPORT_ROWS:
            warnings.append(f"تم الاقتصار على {MAX_IMPORT_ROWS} صف")
            break

        parsed = _map_csv_row(row, _COL_MAP)
        errors = _validate_import_row(parsed)

        rows.append(BulkImportRow(
            row_number=i,
            contract_number=parsed.get("contract_number"),
            title=parsed.get("title"),
            contractor_name=parsed.get("contractor_name"),
            contract_type=parsed.get("contract_type"),
            contract_value=_safe_float(parsed.get("contract_value")),
            start_date=parsed.get("start_date"),
            end_date=parsed.get("end_date"),
            is_valid=len(errors) == 0,
            validation_errors=errors if errors else None,
        ))

    valid_rows = sum(1 for r in rows if r.is_valid)

    return BulkImportPreview(
        total_rows=len(rows),
        valid_rows=valid_rows,
        invalid_rows=len(rows) - valid_rows,
        rows=rows,
        warnings=warnings if warnings else None,
    )


@router.post("/bulk-import/execute-csv", response_model=BulkImportResult)
async def execute_csv_import(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Execute a CSV bulk import. Creates contract records from CSV rows.
    """
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف CSV")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("windows-1256")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    batch_id = uuid.uuid4().hex[:16]

    _COL_MAP = {
        "contract_number": ["contract_number", "رقم العقد", "contract_no", "number", "رقم"],
        "title": ["title", "العنوان", "عنوان العقد", "name"],
        "contractor_name": ["contractor_name", "المقاول", "اسم المقاول", "contractor", "الشركة"],
        "contract_type": ["contract_type", "النوع", "نوع العقد", "type"],
        "contract_value": ["contract_value", "القيمة", "قيمة العقد", "value", "amount"],
        "start_date": ["start_date", "تاريخ البدء", "start", "بداية"],
        "end_date": ["end_date", "تاريخ الانتهاء", "end", "نهاية"],
        "scope_description": ["scope_description", "النطاق", "نطاق العمل", "scope", "الوصف"],
    }

    # Save the CSV file
    upload_dir = os.path.join(settings.UPLOAD_DIR, "contract_intelligence")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{batch_id}.csv"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    documents = []
    errors = []
    successful = 0

    for i, row in enumerate(reader, start=1):
        if i > MAX_IMPORT_ROWS:
            break

        parsed = _map_csv_row(row, _COL_MAP)
        validation_errors = _validate_import_row(parsed)

        # Create document record
        doc = ContractDocument(
            original_filename=file.filename or f"csv_row_{i}",
            stored_path=f"/uploads/contract_intelligence/{filename}",
            file_type="csv",
            processing_status=DocumentProcessingStatus.EXTRACTED,
            extracted_fields=fields_to_json(parsed),
            extraction_confidence=1.0 if not validation_errors else 0.5,
            extraction_notes="; ".join(validation_errors) if validation_errors else "CSV import",
            uploaded_by_id=current_user.id,
            import_batch_id=batch_id,
            import_source="spreadsheet",
        )

        # Classify from extracted data
        classification = classify_contract(extracted_fields=parsed)
        doc.suggested_type = classification.suggested_type
        doc.classification_confidence = classification.confidence
        doc.classification_reason = classification.reason

        # Generate summary
        doc.auto_summary = generate_summary(extracted_fields=parsed, contract_type=classification.suggested_type)

        if validation_errors:
            doc.processing_status = DocumentProcessingStatus.REVIEW
            doc.error_message = "; ".join(validation_errors)
        else:
            doc.processing_status = DocumentProcessingStatus.REVIEW
            successful += 1

        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Risk analysis
        risk_flags = analyze_contract_risks(extracted_fields=parsed)
        if risk_flags:
            save_risk_flags(db, risk_flags, document_id=doc.id)

        documents.append(doc)

    write_audit_log(
        db,
        action="bulk_import_csv",
        entity_type="contract_document",
        user_id=current_user.id,
        description=f"CSV bulk import: {len(documents)} rows, batch={batch_id}",
        request=request,
    )

    # Send batch completion notification
    try:
        failed_count = len(documents) - successful
        if failed_count > len(documents) * BATCH_FAILURE_THRESHOLD and len(documents) > 0:
            notify_intelligence_processing_complete(
                db, event="batch_import_failed",
                batch_id=batch_id,
                details=f"ناجح: {successful}, فاشل: {failed_count} من {len(documents)}",
            )
        else:
            notify_intelligence_processing_complete(
                db, event="batch_import_complete",
                batch_id=batch_id,
                details=f"ناجح: {successful}, فاشل: {failed_count} من {len(documents)}",
            )
    except Exception:
        logger.exception("Batch notification failed (non-fatal)")

    return BulkImportResult(
        total_processed=len(documents),
        successful=successful,
        failed=len(documents) - successful,
        import_batch_id=batch_id,
        documents=documents,
        errors=errors if errors else None,
    )


@router.post("/bulk-import/scan-batch", response_model=BulkImportResult)
async def bulk_scan_import(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Bulk import from multiple scanned files.
    Each file goes through the OCR → extraction → review pipeline.
    """
    batch_id = uuid.uuid4().hex[:16]
    upload_dir = os.path.join(settings.UPLOAD_DIR, "contract_intelligence")
    os.makedirs(upload_dir, exist_ok=True)

    documents = []
    errors = []
    successful = 0

    for file in files[:50]:  # Limit to 50 files per batch
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            errors.append(f"ملف غير مدعوم: {file.filename}")
            continue

        try:
            content = await file.read()
            if len(content) > MAX_DOC_SIZE:
                errors.append(f"ملف كبير جداً: {file.filename}")
                continue

            filename = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(upload_dir, filename)
            with open(filepath, "wb") as f:
                f.write(content)

            stored_path = f"/uploads/contract_intelligence/{filename}"

            doc = ContractDocument(
                original_filename=file.filename or "unknown",
                stored_path=stored_path,
                file_type=ext.lstrip("."),
                file_size=len(content),
                processing_status=DocumentProcessingStatus.QUEUED,
                uploaded_by_id=current_user.id,
                import_batch_id=batch_id,
                import_source="bulk_scan",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            # Process each document
            _process_document(db, doc, filepath, current_user.id, request)

            db.refresh(doc)
            documents.append(doc)

            if doc.processing_status != DocumentProcessingStatus.FAILED:
                successful += 1

        except Exception as e:
            logger.exception("Failed to process file: %s", file.filename)
            errors.append(f"خطأ في معالجة: {file.filename}: {str(e)}")

    write_audit_log(
        db,
        action="bulk_import_scan",
        entity_type="contract_document",
        user_id=current_user.id,
        description=f"Bulk scan import: {len(documents)} files, batch={batch_id}",
        request=request,
    )

    # Send batch completion notification
    try:
        total_failed = len(documents) - successful + len(errors)
        if total_failed > len(documents) * BATCH_FAILURE_THRESHOLD and len(documents) > 0:
            notify_intelligence_processing_complete(
                db, event="batch_import_failed",
                batch_id=batch_id,
                details=f"ناجح: {successful}, فاشل: {total_failed}",
            )
        else:
            notify_intelligence_processing_complete(
                db, event="batch_import_complete",
                batch_id=batch_id,
                details=f"ناجح: {successful}, فاشل: {total_failed}",
            )
    except Exception:
        logger.exception("Batch scan notification failed (non-fatal)")

    return BulkImportResult(
        total_processed=len(documents),
        successful=successful,
        failed=len(documents) - successful + len(errors),
        import_batch_id=batch_id,
        documents=documents,
        errors=errors if errors else None,
    )


# ─────────────────────────────────────────────────────────────
# Contract-level intelligence info
# ─────────────────────────────────────────────────────────────

@router.get("/contracts/{contract_id}/intelligence")
def get_contract_intelligence(
    contract_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """
    Get intelligence data for an existing contract.
    Returns linked documents, risk flags, and duplicates.
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")

    documents = db.query(ContractDocument).filter(
        ContractDocument.contract_id == contract_id
    ).all()

    risk_flags = db.query(ContractRiskFlag).filter(
        (ContractRiskFlag.contract_id == contract_id) |
        (ContractRiskFlag.document_id.in_([d.id for d in documents]) if documents else False)
    ).all()

    duplicates = db.query(ContractDuplicate).filter(
        (ContractDuplicate.contract_id_a == contract_id) |
        (ContractDuplicate.contract_id_b == contract_id)
    ).all()

    return {
        "contract_id": contract_id,
        "documents": [ContractDocumentResponse.model_validate(d) for d in documents],
        "risk_flags": [ContractRiskFlagResponse.model_validate(f) for f in risk_flags],
        "duplicates": [ContractDuplicateResponse.model_validate(d) for d in duplicates],
    }


@router.post("/contracts/{contract_id}/analyze-risks")
def analyze_existing_contract_risks(
    contract_id: int,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Run risk analysis on an existing contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")

    # Clear existing risk flags for this contract
    db.query(ContractRiskFlag).filter(ContractRiskFlag.contract_id == contract_id).delete()
    db.commit()

    risk_flags = analyze_contract_risks(contract=contract)
    saved = save_risk_flags(db, risk_flags, contract_id=contract_id)

    write_audit_log(
        db,
        action="contract_risk_analyze",
        entity_type="contract",
        entity_id=contract_id,
        user_id=current_user.id,
        description=f"Risk analysis: {len(saved)} flags found",
        request=request,
    )

    return {
        "contract_id": contract_id,
        "flags_count": len(saved),
        "flags": [ContractRiskFlagResponse.model_validate(f) for f in saved],
    }


@router.post("/contracts/{contract_id}/detect-duplicates")
def detect_contract_duplicates(
    contract_id: int,
    request: Request,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """Run duplicate detection for an existing contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="العقد غير موجود")

    matches = find_duplicates(
        db,
        contract_number=contract.contract_number,
        contractor_name=contract.contractor_name,
        title=contract.title,
        contract_value=float(contract.contract_value) if contract.contract_value else None,
        start_date=str(contract.start_date) if contract.start_date else None,
        end_date=str(contract.end_date) if contract.end_date else None,
        exclude_contract_id=contract.id,
    )

    saved = save_duplicate_records(
        db,
        document_id=None,
        matches=matches,
        contract_id_a=contract.id,
    )

    write_audit_log(
        db,
        action="contract_duplicate_detect",
        entity_type="contract",
        entity_id=contract_id,
        user_id=current_user.id,
        description=f"Duplicate detection: {len(saved)} matches found",
        request=request,
    )

    return {
        "contract_id": contract_id,
        "matches_count": len(saved),
        "matches": [ContractDuplicateResponse.model_validate(d) for d in saved],
    }


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _map_csv_row(row: dict, col_map: dict) -> dict:
    """Map CSV columns using flexible column name mapping."""
    result = {}
    for target, aliases in col_map.items():
        for alias in aliases:
            if alias in row and row[alias]:
                result[target] = str(row[alias]).strip()
                break
    return result


def _validate_import_row(parsed: dict) -> list:
    """Validate a parsed import row."""
    errors = []
    if not parsed.get("contract_number"):
        errors.append("رقم العقد مفقود")
    if not parsed.get("title"):
        errors.append("العنوان مفقود")
    return errors


def _safe_float(value) -> Optional[float]:
    """Safely convert to float."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


# Column name mapping shared between CSV and Excel
_COL_MAP = {
    "contract_number": ["contract_number", "رقم العقد", "contract_no", "number", "رقم"],
    "title": ["title", "العنوان", "عنوان العقد", "name"],
    "contractor_name": ["contractor_name", "المقاول", "اسم المقاول", "contractor", "الشركة"],
    "contract_type": ["contract_type", "النوع", "نوع العقد", "type"],
    "contract_value": ["contract_value", "القيمة", "قيمة العقد", "value", "amount"],
    "start_date": ["start_date", "تاريخ البدء", "start", "بداية"],
    "end_date": ["end_date", "تاريخ الانتهاء", "end", "نهاية"],
    "scope_description": ["scope_description", "النطاق", "نطاق العمل", "scope", "الوصف"],
}


def _parse_excel_rows(content: bytes) -> tuple:
    """
    Parse Excel (.xlsx) file into list of row dicts + warnings.
    Returns (rows, headers, warnings).
    """
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    warnings = []

    if ws is None:
        return [], [], ["الملف لا يحتوي على أوراق عمل"]

    rows_iter = ws.iter_rows(values_only=False)

    # First row is header
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return [], [], ["الملف فارغ"]

    headers = []
    for cell in header_row:
        val = str(cell.value).strip() if cell.value is not None else ""
        headers.append(val)

    if not any(headers):
        return [], headers, ["لم يتم العثور على عناوين أعمدة"]

    rows = []
    for i, row in enumerate(rows_iter, start=1):
        if i > MAX_IMPORT_ROWS:
            warnings.append(f"تم الاقتصار على {MAX_IMPORT_ROWS} صف")
            break
        row_dict = {}
        for j, cell in enumerate(row):
            if j < len(headers) and headers[j]:
                val = cell.value
                if val is not None:
                    # Handle date objects from Excel
                    if hasattr(val, 'strftime'):
                        val = val.strftime('%Y-%m-%d')
                    row_dict[headers[j]] = str(val).strip()
        if any(row_dict.values()):
            rows.append(row_dict)

    wb.close()
    return rows, headers, warnings


# ─────────────────────────────────────────────────────────────
# Excel Import
# ─────────────────────────────────────────────────────────────

@router.post("/bulk-import/preview-excel", response_model=BulkImportPreview)
async def preview_excel_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Preview an Excel (.xlsx) file for bulk import.
    Returns parsed rows with validation status.
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف Excel (.xlsx)")

    content = await file.read()
    if len(content) > MAX_DOC_SIZE:
        raise HTTPException(status_code=400, detail="حجم الملف كبير جداً")

    try:
        excel_rows, headers, warnings = _parse_excel_rows(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"فشل قراءة ملف Excel: {str(e)}")

    rows = []
    for i, row in enumerate(excel_rows, start=1):
        parsed = _map_csv_row(row, _COL_MAP)
        errors = _validate_import_row(parsed)

        rows.append(BulkImportRow(
            row_number=i,
            contract_number=parsed.get("contract_number"),
            title=parsed.get("title"),
            contractor_name=parsed.get("contractor_name"),
            contract_type=parsed.get("contract_type"),
            contract_value=_safe_float(parsed.get("contract_value")),
            start_date=parsed.get("start_date"),
            end_date=parsed.get("end_date"),
            is_valid=len(errors) == 0,
            validation_errors=errors if errors else None,
        ))

    valid_rows = sum(1 for r in rows if r.is_valid)

    return BulkImportPreview(
        total_rows=len(rows),
        valid_rows=valid_rows,
        invalid_rows=len(rows) - valid_rows,
        rows=rows,
        warnings=warnings if warnings else None,
    )


@router.post("/bulk-import/execute-excel", response_model=BulkImportResult)
async def execute_excel_import(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Execute an Excel bulk import. Creates contract document records from Excel rows.
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف Excel (.xlsx)")

    content = await file.read()
    if len(content) > MAX_DOC_SIZE:
        raise HTTPException(status_code=400, detail="حجم الملف كبير جداً")

    try:
        excel_rows, headers, parse_warnings = _parse_excel_rows(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"فشل قراءة ملف Excel: {str(e)}")

    batch_id = uuid.uuid4().hex[:16]

    # Save the Excel file
    upload_dir = os.path.join(settings.UPLOAD_DIR, "contract_intelligence")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{batch_id}.xlsx"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    documents = []
    errors = list(parse_warnings) if parse_warnings else []
    successful = 0

    for i, row in enumerate(excel_rows, start=1):
        parsed = _map_csv_row(row, _COL_MAP)
        validation_errors = _validate_import_row(parsed)

        doc = ContractDocument(
            original_filename=file.filename or f"excel_row_{i}",
            stored_path=f"/uploads/contract_intelligence/{filename}",
            file_type="xlsx",
            processing_status=DocumentProcessingStatus.EXTRACTED,
            extracted_fields=fields_to_json(parsed),
            extraction_confidence=1.0 if not validation_errors else 0.5,
            extraction_notes="; ".join(validation_errors) if validation_errors else "Excel import",
            uploaded_by_id=current_user.id,
            import_batch_id=batch_id,
            import_source="spreadsheet",
        )

        # Classify from extracted data
        classification = classify_contract(extracted_fields=parsed)
        doc.suggested_type = classification.suggested_type
        doc.classification_confidence = classification.confidence
        doc.classification_reason = classification.reason

        # Generate summary
        doc.auto_summary = generate_summary(extracted_fields=parsed, contract_type=classification.suggested_type)

        if validation_errors:
            doc.processing_status = DocumentProcessingStatus.REVIEW
            doc.error_message = "; ".join(validation_errors)
        else:
            doc.processing_status = DocumentProcessingStatus.REVIEW
            successful += 1

        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Risk analysis
        risk_flags = analyze_contract_risks(extracted_fields=parsed)
        if risk_flags:
            save_risk_flags(db, risk_flags, document_id=doc.id)

        documents.append(doc)

    write_audit_log(
        db,
        action="bulk_import_excel",
        entity_type="contract_document",
        user_id=current_user.id,
        description=f"Excel bulk import: {len(documents)} rows, batch={batch_id}",
        request=request,
    )

    # Send batch completion notification
    try:
        failed_count = len(documents) - successful
        if failed_count > len(documents) * BATCH_FAILURE_THRESHOLD and len(documents) > 0:
            notify_intelligence_processing_complete(
                db, event="batch_import_failed",
                batch_id=batch_id,
                details=f"Excel — ناجح: {successful}, فاشل: {failed_count} من {len(documents)}",
            )
        else:
            notify_intelligence_processing_complete(
                db, event="batch_import_complete",
                batch_id=batch_id,
                details=f"Excel — ناجح: {successful}, فاشل: {failed_count} من {len(documents)}",
            )
    except Exception:
        logger.exception("Excel batch notification failed (non-fatal)")

    return BulkImportResult(
        total_processed=len(documents),
        successful=successful,
        failed=len(documents) - successful,
        import_batch_id=batch_id,
        documents=documents,
        errors=errors if errors else None,
    )


# ─────────────────────────────────────────────────────────────
# OCR Status
# ─────────────────────────────────────────────────────────────

@router.get("/ocr-status")
def get_ocr_system_status(
    current_user: User = Depends(get_current_contracts_manager),
):
    """Return the current OCR engine status and capabilities."""
    return get_ocr_status()


# ─────────────────────────────────────────────────────────────
# Intelligence Reports (with filters)
# ─────────────────────────────────────────────────────────────

def _apply_document_filters(
    query,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    ocr_status: Optional[str] = None,
    review_status: Optional[str] = None,
    classification_type: Optional[str] = None,
    import_source: Optional[str] = None,
    search: Optional[str] = None,
):
    """Apply common filter parameters to a ContractDocument query."""
    if date_from:
        try:
            from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(ContractDocument.created_at >= from_dt)
        except ValueError:
            pass
    if date_to:
        try:
            to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            # Include the whole day
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(ContractDocument.created_at <= to_dt)
        except ValueError:
            pass
    if ocr_status:
        status_map = {
            "complete": [DocumentProcessingStatus.OCR_COMPLETE, DocumentProcessingStatus.EXTRACTED,
                         DocumentProcessingStatus.REVIEW, DocumentProcessingStatus.APPROVED],
            "pending": [DocumentProcessingStatus.QUEUED, DocumentProcessingStatus.PROCESSING],
            "failed": [DocumentProcessingStatus.FAILED],
        }
        if ocr_status in status_map:
            query = query.filter(ContractDocument.processing_status.in_(status_map[ocr_status]))
    if review_status:
        try:
            status_enum = DocumentProcessingStatus(review_status)
            query = query.filter(ContractDocument.processing_status == status_enum)
        except ValueError:
            pass
    if classification_type:
        query = query.filter(ContractDocument.suggested_type == classification_type)
    if import_source:
        query = query.filter(ContractDocument.import_source == import_source)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (ContractDocument.original_filename.ilike(search_pattern)) |
            (ContractDocument.extracted_fields.ilike(search_pattern)) |
            (ContractDocument.auto_summary.ilike(search_pattern)) |
            (ContractDocument.import_batch_id.ilike(search_pattern))
        )
    return query


@router.get("/reports")
def get_intelligence_reports(
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    ocr_status: Optional[str] = Query(None, description="Filter by OCR status: complete|pending|failed"),
    review_status: Optional[str] = Query(None, description="Filter by review status enum value"),
    classification_type: Optional[str] = Query(None, description="Filter by classification type"),
    risk_severity: Optional[str] = Query(None, description="Filter risks by severity: critical|high|medium|low"),
    risk_type: Optional[str] = Query(None, description="Filter risks by type"),
    duplicate_status: Optional[str] = Query(None, description="Filter duplicates: pending|confirmed_same|confirmed_different"),
    import_source: Optional[str] = Query(None, description="Filter by import source: upload|bulk_scan|spreadsheet"),
    search: Optional[str] = Query(None, description="Keyword search across filenames, fields, summaries"),
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Comprehensive intelligence reports using real backend data.
    Supports filtering by date range, status, classification, risk, and keyword search.
    """
    # Base query with filters applied
    base_query = db.query(ContractDocument.id)
    base_query = _apply_document_filters(
        base_query, date_from, date_to, ocr_status, review_status,
        classification_type, import_source, search,
    )
    filtered_ids = [row[0] for row in base_query.all()]

    # 1. Processing pipeline status counts (on filtered set)
    status_counts = {}
    for s in DocumentProcessingStatus:
        if filtered_ids:
            count = db.query(sql_func.count(ContractDocument.id)).filter(
                ContractDocument.id.in_(filtered_ids),
                ContractDocument.processing_status == s
            ).scalar() or 0
        else:
            count = 0
        status_counts[s.value] = count

    total_documents = sum(status_counts.values())

    # 2. Import source breakdown (on filtered set)
    source_counts = {}
    for source in ["upload", "bulk_scan", "spreadsheet"]:
        if filtered_ids:
            count = db.query(sql_func.count(ContractDocument.id)).filter(
                ContractDocument.id.in_(filtered_ids),
                ContractDocument.import_source == source
            ).scalar() or 0
        else:
            count = 0
        source_counts[source] = count

    # 3. Classification distribution (on filtered set)
    cls_q = db.query(
        ContractDocument.suggested_type,
        sql_func.count(ContractDocument.id),
    ).filter(
        ContractDocument.suggested_type.isnot(None),
    )
    if filtered_ids:
        cls_q = cls_q.filter(ContractDocument.id.in_(filtered_ids))
    classification_rows = cls_q.group_by(ContractDocument.suggested_type).all()

    classification_dist = {row[0]: row[1] for row in classification_rows}

    # 4. Risk flags by severity (filtered by document IDs if applicable)
    risk_base = db.query(ContractRiskFlag)
    if filtered_ids:
        risk_base = risk_base.filter(ContractRiskFlag.document_id.in_(filtered_ids))
    if risk_severity:
        try:
            sev_enum = RiskSeverity(risk_severity)
            risk_base = risk_base.filter(ContractRiskFlag.severity == sev_enum)
        except ValueError:
            pass
    if risk_type:
        risk_base = risk_base.filter(ContractRiskFlag.risk_type == risk_type)

    risk_ids = [r.id for r in risk_base.all()]

    risk_severity_rows = db.query(
        ContractRiskFlag.severity,
        sql_func.count(ContractRiskFlag.id),
    )
    if risk_ids:
        risk_severity_rows = risk_severity_rows.filter(ContractRiskFlag.id.in_(risk_ids))
    risk_severity_rows = risk_severity_rows.group_by(ContractRiskFlag.severity).all()

    risk_by_severity = {row[0].value if hasattr(row[0], 'value') else str(row[0]): row[1] for row in risk_severity_rows}

    # 5. Risk flags by type (top 10, filtered)
    risk_type_q = db.query(
        ContractRiskFlag.risk_type,
        sql_func.count(ContractRiskFlag.id),
    )
    if risk_ids:
        risk_type_q = risk_type_q.filter(ContractRiskFlag.id.in_(risk_ids))
    risk_type_rows = risk_type_q.group_by(ContractRiskFlag.risk_type).order_by(
        sql_func.count(ContractRiskFlag.id).desc()
    ).limit(10).all()

    risk_by_type = {row[0]: row[1] for row in risk_type_rows}

    # 6. Unresolved vs resolved risks (filtered)
    resolved_q = db.query(sql_func.count(ContractRiskFlag.id)).filter(ContractRiskFlag.is_resolved == True)
    unresolved_q = db.query(sql_func.count(ContractRiskFlag.id)).filter(ContractRiskFlag.is_resolved == False)
    if risk_ids:
        resolved_q = resolved_q.filter(ContractRiskFlag.id.in_(risk_ids))
        unresolved_q = unresolved_q.filter(ContractRiskFlag.id.in_(risk_ids))
    resolved_risks = resolved_q.scalar() or 0
    unresolved_risks = unresolved_q.scalar() or 0

    # 7. Duplicate candidates (filtered)
    dup_base = db.query(ContractDuplicate)
    if filtered_ids:
        dup_base = dup_base.filter(ContractDuplicate.document_id.in_(filtered_ids))
    if duplicate_status:
        try:
            dup_enum = DuplicateStatus(duplicate_status)
            dup_base = dup_base.filter(ContractDuplicate.status == dup_enum)
        except ValueError:
            pass

    total_dups = dup_base.count()
    pending_dups = dup_base.filter(ContractDuplicate.status == DuplicateStatus.PENDING).count()
    confirmed_same = dup_base.filter(ContractDuplicate.status == DuplicateStatus.CONFIRMED_SAME).count()
    confirmed_diff = dup_base.filter(ContractDuplicate.status == DuplicateStatus.CONFIRMED_DIFFERENT).count()

    # 8. OCR confidence distribution (filtered)
    ocr_high_q = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.ocr_confidence >= 0.7
    )
    ocr_medium_q = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.ocr_confidence >= 0.3,
        ContractDocument.ocr_confidence < 0.7,
    )
    ocr_low_q = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.ocr_confidence.isnot(None),
        ContractDocument.ocr_confidence < 0.3,
    )
    avg_ocr_q = db.query(sql_func.avg(ContractDocument.ocr_confidence)).filter(
        ContractDocument.ocr_confidence.isnot(None)
    )
    if filtered_ids:
        ocr_high_q = ocr_high_q.filter(ContractDocument.id.in_(filtered_ids))
        ocr_medium_q = ocr_medium_q.filter(ContractDocument.id.in_(filtered_ids))
        ocr_low_q = ocr_low_q.filter(ContractDocument.id.in_(filtered_ids))
        avg_ocr_q = avg_ocr_q.filter(ContractDocument.id.in_(filtered_ids))

    ocr_high = ocr_high_q.scalar() or 0
    ocr_medium = ocr_medium_q.scalar() or 0
    ocr_low = ocr_low_q.scalar() or 0
    avg_ocr = avg_ocr_q.scalar()

    # 9. Review queue size (filtered)
    review_q = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.processing_status == DocumentProcessingStatus.REVIEW
    )
    if filtered_ids:
        review_q = review_q.filter(ContractDocument.id.in_(filtered_ids))
    review_queue = review_q.scalar() or 0

    # 10. Batch import results (filtered)
    batch_q = db.query(
        ContractDocument.import_batch_id,
        ContractDocument.import_source,
        sql_func.count(ContractDocument.id),
        sql_func.min(ContractDocument.created_at),
    ).filter(
        ContractDocument.import_batch_id.isnot(None),
    )
    if filtered_ids:
        batch_q = batch_q.filter(ContractDocument.id.in_(filtered_ids))
    batch_rows = batch_q.group_by(
        ContractDocument.import_batch_id,
        ContractDocument.import_source,
    ).order_by(sql_func.min(ContractDocument.created_at).desc()).limit(20).all()

    batch_results = []
    for batch_id, source, count, created in batch_rows:
        failed_in_batch = db.query(sql_func.count(ContractDocument.id)).filter(
            ContractDocument.import_batch_id == batch_id,
            ContractDocument.processing_status == DocumentProcessingStatus.FAILED,
        ).scalar() or 0
        batch_results.append({
            "batch_id": batch_id,
            "source": source,
            "total": count,
            "failed": failed_in_batch,
            "successful": count - failed_in_batch,
            "created_at": created.isoformat() if created else None,
        })

    # 11. Contracts digitized (filtered)
    digitized_q = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.contract_id.isnot(None)
    )
    if filtered_ids:
        digitized_q = digitized_q.filter(ContractDocument.id.in_(filtered_ids))
    digitized = digitized_q.scalar() or 0

    # 12. OCR engine info
    ocr_status_info = get_ocr_status()

    # 13. Time-series data: documents processed per day (last 90 days)
    # Use string-based date extraction for SQLite compatibility
    _date_col = sql_func.substr(sql_func.cast(ContractDocument.created_at, String), 1, 10)
    timeseries_rows = db.query(
        _date_col.label("date"),
        sql_func.count(ContractDocument.id).label("count"),
    )
    if filtered_ids:
        timeseries_rows = timeseries_rows.filter(ContractDocument.id.in_(filtered_ids))
    timeseries_rows = timeseries_rows.filter(
        ContractDocument.created_at.isnot(None)
    ).group_by(_date_col).order_by(_date_col).limit(90).all()

    documents_over_time = [
        {"date": str(row[0]) if row[0] else None, "count": row[1]}
        for row in timeseries_rows
    ]

    # 14. Risk flags over time
    _risk_date_col = sql_func.substr(sql_func.cast(ContractRiskFlag.created_at, String), 1, 10)
    risk_ts_rows = db.query(
        _risk_date_col.label("date"),
        sql_func.count(ContractRiskFlag.id).label("count"),
    )
    if risk_ids:
        risk_ts_rows = risk_ts_rows.filter(ContractRiskFlag.id.in_(risk_ids))
    risk_ts_rows = risk_ts_rows.filter(
        ContractRiskFlag.created_at.isnot(None)
    ).group_by(_risk_date_col).order_by(_risk_date_col).limit(90).all()

    risks_over_time = [
        {"date": str(row[0]) if row[0] else None, "count": row[1]}
        for row in risk_ts_rows
    ]

    # 15. Active filters summary
    active_filters = {}
    if date_from:
        active_filters["date_from"] = date_from
    if date_to:
        active_filters["date_to"] = date_to
    if ocr_status:
        active_filters["ocr_status"] = ocr_status
    if review_status:
        active_filters["review_status"] = review_status
    if classification_type:
        active_filters["classification_type"] = classification_type
    if risk_severity:
        active_filters["risk_severity"] = risk_severity
    if risk_type:
        active_filters["risk_type"] = risk_type
    if duplicate_status:
        active_filters["duplicate_status"] = duplicate_status
    if import_source:
        active_filters["import_source"] = import_source
    if search:
        active_filters["search"] = search

    return {
        "total_documents": total_documents,
        "status_breakdown": status_counts,
        "import_sources": source_counts,
        "classification_distribution": classification_dist,
        "risk_by_severity": risk_by_severity,
        "risk_by_type": risk_by_type,
        "risks_resolved": resolved_risks,
        "risks_unresolved": unresolved_risks,
        "duplicates_total": total_dups,
        "duplicates_pending": pending_dups,
        "duplicates_confirmed_same": confirmed_same,
        "duplicates_confirmed_different": confirmed_diff,
        "ocr_confidence": {
            "high": ocr_high,
            "medium": ocr_medium,
            "low": ocr_low,
            "average": round(avg_ocr, 3) if avg_ocr is not None else None,
        },
        "review_queue_size": review_queue,
        "batch_results": batch_results,
        "contracts_digitized": digitized,
        "ocr_engine": ocr_status_info,
        "documents_over_time": documents_over_time,
        "risks_over_time": risks_over_time,
        "active_filters": active_filters,
    }


# ─────────────────────────────────────────────────────────────
# Data Export (CSV + PDF)
# ─────────────────────────────────────────────────────────────

@router.get("/reports/export/csv")
def export_intelligence_csv(
    section: str = Query("all", description="Section: all|documents|risks|duplicates|batches"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    ocr_status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    classification_type: Optional[str] = Query(None),
    risk_severity: Optional[str] = Query(None),
    import_source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    request: Request = None,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Export intelligence report data as CSV.
    Respects active filters.
    """
    from fastapi.responses import StreamingResponse

    output = io.StringIO()
    writer = csv.writer(output)

    # Build filtered document query
    doc_query = db.query(ContractDocument)
    doc_query = _apply_document_filters(
        doc_query, date_from, date_to, ocr_status, review_status,
        classification_type, import_source, search,
    )
    documents = doc_query.order_by(ContractDocument.created_at.desc()).all()
    doc_ids = [d.id for d in documents]

    if section in ("all", "documents"):
        writer.writerow([
            "ID", "Filename", "Status", "OCR Engine", "OCR Confidence",
            "Extraction Confidence", "Classification", "Classification Confidence",
            "Import Source", "Batch ID", "Created At", "Summary",
        ])
        for doc in documents:
            fields = fields_from_json(doc.extracted_fields) if doc.extracted_fields else {}
            writer.writerow([
                doc.id,
                doc.original_filename,
                doc.processing_status.value if doc.processing_status else "",
                doc.ocr_engine or "",
                round(doc.ocr_confidence, 3) if doc.ocr_confidence else "",
                round(doc.extraction_confidence, 3) if doc.extraction_confidence else "",
                doc.suggested_type or "",
                round(doc.classification_confidence, 3) if doc.classification_confidence else "",
                doc.import_source or "",
                doc.import_batch_id or "",
                doc.created_at.isoformat() if doc.created_at else "",
                (doc.auto_summary or "")[:200],
            ])
        writer.writerow([])

    if section in ("all", "risks"):
        writer.writerow(["--- Risk Flags ---"])
        writer.writerow([
            "ID", "Document ID", "Risk Type", "Severity",
            "Description", "Is Resolved", "Created At",
        ])
        risk_q = db.query(ContractRiskFlag)
        if doc_ids:
            risk_q = risk_q.filter(ContractRiskFlag.document_id.in_(doc_ids))
        if risk_severity:
            try:
                risk_q = risk_q.filter(ContractRiskFlag.severity == RiskSeverity(risk_severity))
            except ValueError:
                pass
        for risk in risk_q.order_by(ContractRiskFlag.created_at.desc()).all():
            writer.writerow([
                risk.id,
                risk.document_id or "",
                risk.risk_type,
                risk.severity.value if risk.severity else "",
                risk.description,
                "Yes" if risk.is_resolved else "No",
                risk.created_at.isoformat() if risk.created_at else "",
            ])
        writer.writerow([])

    if section in ("all", "duplicates"):
        writer.writerow(["--- Duplicate Candidates ---"])
        writer.writerow([
            "ID", "Document ID", "Contract A", "Contract B",
            "Similarity Score", "Status", "Match Reasons", "Created At",
        ])
        dup_q = db.query(ContractDuplicate)
        if doc_ids:
            dup_q = dup_q.filter(ContractDuplicate.document_id.in_(doc_ids))
        for dup in dup_q.order_by(ContractDuplicate.created_at.desc()).all():
            writer.writerow([
                dup.id,
                dup.document_id or "",
                dup.contract_id_a or "",
                dup.contract_id_b or "",
                round(dup.similarity_score, 3) if dup.similarity_score else "",
                dup.status.value if dup.status else "",
                dup.match_reasons or "",
                dup.created_at.isoformat() if dup.created_at else "",
            ])
        writer.writerow([])

    if section in ("all", "batches"):
        writer.writerow(["--- Batch Import Results ---"])
        writer.writerow(["Batch ID", "Source", "Total", "Failed", "Created At"])
        batch_q = db.query(
            ContractDocument.import_batch_id,
            ContractDocument.import_source,
            sql_func.count(ContractDocument.id),
            sql_func.min(ContractDocument.created_at),
        ).filter(
            ContractDocument.import_batch_id.isnot(None),
        )
        if doc_ids:
            batch_q = batch_q.filter(ContractDocument.id.in_(doc_ids))
        for batch_id, source, count, created in batch_q.group_by(
            ContractDocument.import_batch_id, ContractDocument.import_source
        ).order_by(sql_func.min(ContractDocument.created_at).desc()).limit(50).all():
            failed = db.query(sql_func.count(ContractDocument.id)).filter(
                ContractDocument.import_batch_id == batch_id,
                ContractDocument.processing_status == DocumentProcessingStatus.FAILED,
            ).scalar() or 0
            writer.writerow([
                batch_id, source or "", count, failed,
                created.isoformat() if created else "",
            ])

    write_audit_log(
        db, action="intelligence_report_export_csv",
        entity_type="intelligence_report",
        user_id=current_user.id,
        description=f"CSV export: section={section}",
        request=request,
    )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=intelligence_report.csv"},
    )


@router.get("/reports/export/pdf")
def export_intelligence_pdf(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    ocr_status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    classification_type: Optional[str] = Query(None),
    risk_severity: Optional[str] = Query(None),
    import_source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    request: Request = None,
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Export intelligence report summary as PDF.
    Uses reportlab (already in requirements.txt).
    """
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Build filtered document query
    doc_query = db.query(ContractDocument)
    doc_query = _apply_document_filters(
        doc_query, date_from, date_to, ocr_status, review_status,
        classification_type, import_source, search,
    )
    documents = doc_query.order_by(ContractDocument.created_at.desc()).all()
    doc_ids = [d.id for d in documents]

    # Compute stats
    total_docs = len(documents)
    status_breakdown = {}
    for doc in documents:
        s = doc.processing_status.value if doc.processing_status else "unknown"
        status_breakdown[s] = status_breakdown.get(s, 0) + 1

    risk_q = db.query(ContractRiskFlag)
    if doc_ids:
        risk_q = risk_q.filter(ContractRiskFlag.document_id.in_(doc_ids))
    total_risks = risk_q.count()
    unresolved = risk_q.filter(ContractRiskFlag.is_resolved == False).count()

    dup_q = db.query(ContractDuplicate)
    if doc_ids:
        dup_q = dup_q.filter(ContractDuplicate.document_id.in_(doc_ids))
    total_dups_pdf = dup_q.count()

    # Build PDF
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 30 * mm

    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(30 * mm, y, "Contract Intelligence Report")
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    c.drawString(30 * mm, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 6 * mm

    # Active filters
    filter_parts = []
    if date_from:
        filter_parts.append(f"From: {date_from}")
    if date_to:
        filter_parts.append(f"To: {date_to}")
    if ocr_status:
        filter_parts.append(f"OCR: {ocr_status}")
    if review_status:
        filter_parts.append(f"Review: {review_status}")
    if classification_type:
        filter_parts.append(f"Type: {classification_type}")
    if risk_severity:
        filter_parts.append(f"Risk: {risk_severity}")
    if import_source:
        filter_parts.append(f"Source: {import_source}")
    if search:
        filter_parts.append(f"Search: {search}")
    if filter_parts:
        c.drawString(30 * mm, y, f"Filters: {', '.join(filter_parts)}")
        y -= 6 * mm

    y -= 5 * mm

    # Summary section
    c.setFont("Helvetica-Bold", 13)
    c.drawString(30 * mm, y, "Summary")
    y -= 7 * mm
    c.setFont("Helvetica", 10)

    summary_items = [
        f"Total Documents: {total_docs}",
        f"Total Risk Flags: {total_risks} (Unresolved: {unresolved})",
        f"Total Duplicate Candidates: {total_dups_pdf}",
    ]
    for item in summary_items:
        c.drawString(35 * mm, y, item)
        y -= 5 * mm

    y -= 3 * mm

    # Status breakdown
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "Processing Status")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    for status, count in sorted(status_breakdown.items()):
        c.drawString(35 * mm, y, f"{status}: {count}")
        y -= 5 * mm

    y -= 3 * mm

    # Document list (top 50)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, f"Documents (showing up to 50 of {total_docs})")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    for doc in documents[:50]:
        if y < 25 * mm:
            c.showPage()
            y = height - 20 * mm
            c.setFont("Helvetica", 8)
        line = f"#{doc.id} | {doc.original_filename[:40]} | {doc.processing_status.value if doc.processing_status else '?'} | {doc.suggested_type or '-'}"
        c.drawString(30 * mm, y, line)
        y -= 4 * mm

    write_audit_log(
        db, action="intelligence_report_export_pdf",
        entity_type="intelligence_report",
        user_id=current_user.id,
        description="PDF export",
        request=request,
    )

    c.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=intelligence_report.pdf"},
    )
