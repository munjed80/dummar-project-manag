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
from sqlalchemy import func as sql_func
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
# Intelligence Reports
# ─────────────────────────────────────────────────────────────

@router.get("/reports")
def get_intelligence_reports(
    current_user: User = Depends(get_current_contracts_manager),
    db: Session = Depends(get_db),
):
    """
    Comprehensive intelligence reports using real backend data.
    Returns structured data for dashboard charts and tables.
    """
    # 1. Processing pipeline status counts
    status_counts = {}
    for s in DocumentProcessingStatus:
        count = db.query(sql_func.count(ContractDocument.id)).filter(
            ContractDocument.processing_status == s
        ).scalar() or 0
        status_counts[s.value] = count

    total_documents = sum(status_counts.values())

    # 2. Import source breakdown
    source_counts = {}
    for source in ["upload", "bulk_scan", "spreadsheet"]:
        count = db.query(sql_func.count(ContractDocument.id)).filter(
            ContractDocument.import_source == source
        ).scalar() or 0
        source_counts[source] = count

    # 3. Classification distribution
    classification_rows = db.query(
        ContractDocument.suggested_type,
        sql_func.count(ContractDocument.id),
    ).filter(
        ContractDocument.suggested_type.isnot(None),
    ).group_by(ContractDocument.suggested_type).all()

    classification_dist = {row[0]: row[1] for row in classification_rows}

    # 4. Risk flags by severity
    risk_severity_rows = db.query(
        ContractRiskFlag.severity,
        sql_func.count(ContractRiskFlag.id),
    ).group_by(ContractRiskFlag.severity).all()

    risk_by_severity = {row[0].value if hasattr(row[0], 'value') else str(row[0]): row[1] for row in risk_severity_rows}

    # 5. Risk flags by type (top 10)
    risk_type_rows = db.query(
        ContractRiskFlag.risk_type,
        sql_func.count(ContractRiskFlag.id),
    ).group_by(ContractRiskFlag.risk_type).order_by(
        sql_func.count(ContractRiskFlag.id).desc()
    ).limit(10).all()

    risk_by_type = {row[0]: row[1] for row in risk_type_rows}

    # 6. Unresolved vs resolved risks
    resolved_risks = db.query(sql_func.count(ContractRiskFlag.id)).filter(
        ContractRiskFlag.is_resolved == True
    ).scalar() or 0
    unresolved_risks = db.query(sql_func.count(ContractRiskFlag.id)).filter(
        ContractRiskFlag.is_resolved == False
    ).scalar() or 0

    # 7. Duplicate candidates
    total_dups = db.query(sql_func.count(ContractDuplicate.id)).scalar() or 0
    pending_dups = db.query(sql_func.count(ContractDuplicate.id)).filter(
        ContractDuplicate.status == DuplicateStatus.PENDING
    ).scalar() or 0
    confirmed_same = db.query(sql_func.count(ContractDuplicate.id)).filter(
        ContractDuplicate.status == DuplicateStatus.CONFIRMED_SAME
    ).scalar() or 0
    confirmed_diff = db.query(sql_func.count(ContractDuplicate.id)).filter(
        ContractDuplicate.status == DuplicateStatus.CONFIRMED_DIFFERENT
    ).scalar() or 0

    # 8. OCR confidence distribution
    ocr_high = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.ocr_confidence >= 0.7
    ).scalar() or 0
    ocr_medium = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.ocr_confidence >= 0.3,
        ContractDocument.ocr_confidence < 0.7,
    ).scalar() or 0
    ocr_low = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.ocr_confidence.isnot(None),
        ContractDocument.ocr_confidence < 0.3,
    ).scalar() or 0

    avg_ocr = db.query(sql_func.avg(ContractDocument.ocr_confidence)).filter(
        ContractDocument.ocr_confidence.isnot(None)
    ).scalar()

    # 9. Review queue size
    review_queue = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.processing_status == DocumentProcessingStatus.REVIEW
    ).scalar() or 0

    # 10. Batch import results
    batch_rows = db.query(
        ContractDocument.import_batch_id,
        ContractDocument.import_source,
        sql_func.count(ContractDocument.id),
        sql_func.min(ContractDocument.created_at),
    ).filter(
        ContractDocument.import_batch_id.isnot(None),
    ).group_by(
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

    # 11. Contracts digitized (documents converted to contracts)
    digitized = db.query(sql_func.count(ContractDocument.id)).filter(
        ContractDocument.contract_id.isnot(None)
    ).scalar() or 0

    # 12. OCR engine info
    ocr_status = get_ocr_status()

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
        "ocr_engine": ocr_status,
    }
