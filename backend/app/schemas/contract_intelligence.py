from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.contract_intelligence import DocumentProcessingStatus, RiskSeverity, DuplicateStatus


# --- Extracted Fields ---

class ExtractedFieldsSchema(BaseModel):
    contract_number: Optional[str] = None
    title: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_contact: Optional[str] = None
    contract_type: Optional[str] = None
    contract_value: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    scope_description: Optional[str] = None
    related_areas: Optional[str] = None
    additional_fields: Optional[dict] = None


# --- Contract Document ---

class ContractDocumentCreate(BaseModel):
    original_filename: str
    stored_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    import_batch_id: Optional[str] = None
    import_source: Optional[str] = None


class ContractDocumentUpdate(BaseModel):
    processing_status: Optional[DocumentProcessingStatus] = None
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_engine: Optional[str] = None
    extracted_fields: Optional[str] = None
    extraction_confidence: Optional[float] = None
    extraction_notes: Optional[str] = None
    suggested_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_reason: Optional[str] = None
    auto_summary: Optional[str] = None
    edited_summary: Optional[str] = None
    contract_id: Optional[int] = None
    error_message: Optional[str] = None


class ContractDocumentResponse(BaseModel):
    id: int
    original_filename: str
    stored_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    processing_status: DocumentProcessingStatus
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_engine: Optional[str] = None
    ocr_completed_at: Optional[datetime] = None
    extracted_fields: Optional[str] = None
    extraction_confidence: Optional[float] = None
    extraction_notes: Optional[str] = None
    suggested_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_reason: Optional[str] = None
    auto_summary: Optional[str] = None
    edited_summary: Optional[str] = None
    contract_id: Optional[int] = None
    import_batch_id: Optional[str] = None
    import_source: Optional[str] = None
    uploaded_by_id: int
    reviewed_by_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# --- Risk Flags ---

class ContractRiskFlagResponse(BaseModel):
    id: int
    document_id: Optional[int] = None
    contract_id: Optional[int] = None
    risk_type: str
    severity: RiskSeverity
    description: str
    details: Optional[str] = None
    is_resolved: bool
    resolved_by_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Duplicates ---

class ContractDuplicateResponse(BaseModel):
    id: int
    document_id: Optional[int] = None
    contract_id_a: Optional[int] = None
    contract_id_b: Optional[int] = None
    similarity_score: Optional[float] = None
    match_reasons: Optional[str] = None
    status: DuplicateStatus
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ContractDuplicateReview(BaseModel):
    status: DuplicateStatus
    review_notes: Optional[str] = None


# --- Bulk Import ---

class BulkImportRow(BaseModel):
    row_number: int
    filename: Optional[str] = None
    contract_number: Optional[str] = None
    title: Optional[str] = None
    contractor_name: Optional[str] = None
    contract_type: Optional[str] = None
    contract_value: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_valid: bool = True
    validation_errors: Optional[List[str]] = None


class BulkImportPreview(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: List[BulkImportRow]
    warnings: Optional[List[str]] = None


class BulkImportResult(BaseModel):
    total_processed: int
    successful: int
    failed: int
    import_batch_id: str
    documents: List[ContractDocumentResponse]
    errors: Optional[List[str]] = None


# --- Dashboard Stats ---

class IntelligenceDashboardStats(BaseModel):
    total_documents: int = 0
    queued: int = 0
    processing: int = 0
    ocr_complete: int = 0
    extracted: int = 0
    review: int = 0
    approved: int = 0
    rejected: int = 0
    failed: int = 0
    total_risk_flags: int = 0
    unresolved_risk_flags: int = 0
    critical_risks: int = 0
    high_risks: int = 0
    total_duplicates: int = 0
    pending_duplicates: int = 0
    avg_ocr_confidence: Optional[float] = None
    avg_extraction_confidence: Optional[float] = None


# --- Processing Queue ---

class ProcessingQueueResponse(BaseModel):
    queue_length: int
    documents: List[ContractDocumentResponse]
    status_filter: Optional[DocumentProcessingStatus] = None
