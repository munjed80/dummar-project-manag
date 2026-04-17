from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class DocumentProcessingStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    OCR_COMPLETE = "ocr_complete"
    EXTRACTED = "extracted"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class RiskSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DuplicateStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED_SAME = "confirmed_same"
    CONFIRMED_DIFFERENT = "confirmed_different"
    REVIEW_LATER = "review_later"


class ContractDocument(Base):
    """Represents a scanned/uploaded document going through the intelligence pipeline."""
    __tablename__ = "contract_documents"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(500), nullable=False)
    stored_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)  # pdf, jpg, png, csv, xlsx
    file_size = Column(Integer, nullable=True)

    processing_status = Column(SQLEnum(DocumentProcessingStatus), nullable=False, default=DocumentProcessingStatus.QUEUED)

    # OCR results
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ocr_engine = Column(String(100), nullable=True)
    ocr_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Extracted fields (JSON stored as Text for SQLite compat)
    extracted_fields = Column(Text, nullable=True)  # JSON
    extraction_confidence = Column(Float, nullable=True)
    extraction_notes = Column(Text, nullable=True)

    # Classification
    suggested_type = Column(String(50), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    classification_reason = Column(Text, nullable=True)

    # Summary
    auto_summary = Column(Text, nullable=True)
    edited_summary = Column(Text, nullable=True)

    # Link to final contract record
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    # Import batch tracking
    import_batch_id = Column(String(100), nullable=True, index=True)
    import_source = Column(String(50), nullable=True)  # upload, bulk_scan, spreadsheet

    # User tracking
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Relationships
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    contract = relationship("Contract", foreign_keys=[contract_id])
    risk_flags = relationship("ContractRiskFlag", back_populates="document", cascade="all, delete-orphan")
    duplicate_matches = relationship("ContractDuplicate", foreign_keys="ContractDuplicate.document_id", back_populates="document", cascade="all, delete-orphan")


class ContractRiskFlag(Base):
    """Risk flags identified for a contract document."""
    __tablename__ = "contract_risk_flags"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("contract_documents.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    risk_type = Column(String(100), nullable=False)
    severity = Column(SQLEnum(RiskSeverity), nullable=False, default=RiskSeverity.LOW)
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=True)

    is_resolved = Column(Boolean, default=False)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("ContractDocument", back_populates="risk_flags")
    contract = relationship("Contract", foreign_keys=[contract_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class ContractDuplicate(Base):
    """Tracks potential duplicate/similar contract pairs."""
    __tablename__ = "contract_duplicates"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("contract_documents.id"), nullable=True)
    contract_id_a = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    contract_id_b = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    similarity_score = Column(Float, nullable=True)
    match_reasons = Column(Text, nullable=True)  # JSON array of reasons

    status = Column(SQLEnum(DuplicateStatus), nullable=False, default=DuplicateStatus.PENDING)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("ContractDocument", back_populates="duplicate_matches", foreign_keys=[document_id])
    contract_a = relationship("Contract", foreign_keys=[contract_id_a])
    contract_b = relationship("Contract", foreign_keys=[contract_id_b])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
