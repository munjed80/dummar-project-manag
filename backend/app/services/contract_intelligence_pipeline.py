"""Contract-document intelligence pipeline.

Encapsulates the multi-step processing performed on every uploaded
contract document (OCR → extraction → classification → summary →
risk analysis → duplicate detection → notifications). The pipeline is
deliberately **side-effecting on a single ContractDocument row** so it
can be invoked from either an HTTP request handler or a Celery task.

The function previously lived inline in ``app.api.contract_intelligence``
as ``_process_document``. Extracting it here lets the background-job
worker share exactly the same logic the API uses without dragging the
FastAPI ``Request`` object across a process boundary.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.contract_intelligence import ContractDocument, DocumentProcessingStatus
from app.services.audit import write_audit_log
from app.services.classification_service import classify_contract
from app.services.duplicate_service import find_duplicates, save_duplicate_records
from app.services.extraction_service import extract_fields, fields_to_json
from app.services.notification_service import notify_intelligence_processing_complete
from app.services.ocr_service import process_ocr
from app.services.risk_service import analyze_contract_risks, save_risk_flags
from app.services.summary_service import generate_summary

logger = logging.getLogger("dummar.contract_intelligence.pipeline")


def run_intelligence_pipeline(
    db: Session,
    doc: ContractDocument,
    filepath: str,
    user_id: int,
) -> None:
    """Run the full intelligence pipeline on *doc*.

    All exceptions are caught and recorded on the document row so a single
    bad upload never tears down the worker process. The function commits
    after each phase so a partial result is still observable through the
    Processing Queue UI even if a later phase fails.
    """
    try:
        # Step 1: OCR
        doc.processing_status = DocumentProcessingStatus.PROCESSING
        db.commit()

        ocr_result = process_ocr(filepath, doc.file_type or "")

        doc.ocr_text = ocr_result.text
        doc.ocr_confidence = ocr_result.confidence
        doc.ocr_engine = ocr_result.engine
        doc.ocr_completed_at = datetime.now(timezone.utc)

        if not ocr_result.success:
            doc.processing_status = DocumentProcessingStatus.FAILED
            doc.error_message = (
                "; ".join(ocr_result.warnings) if ocr_result.warnings else "OCR failed"
            )
            db.commit()
            return

        doc.processing_status = DocumentProcessingStatus.OCR_COMPLETE
        db.commit()

        # Step 2: Field extraction
        extraction_result = extract_fields(ocr_result.text)
        doc.extracted_fields = fields_to_json(extraction_result.fields)
        doc.extraction_confidence = extraction_result.confidence
        doc.extraction_notes = (
            "; ".join(extraction_result.notes) if extraction_result.notes else None
        )

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

        # Final status (always REVIEW — manager confirms before linking)
        doc.processing_status = DocumentProcessingStatus.REVIEW
        db.commit()

        write_audit_log(
            db,
            action="contract_doc_processed",
            entity_type="contract_document",
            entity_id=doc.id,
            user_id=user_id,
            description=(
                f"Document processed: OCR={doc.ocr_confidence}, "
                f"extraction={doc.extraction_confidence}"
            ),
            request=None,
        )

        # Notifications (non-fatal)
        try:
            notify_intelligence_processing_complete(
                db,
                event="extraction_review_ready",
                document_id=doc.id,
                details=(
                    f"ثقة OCR: {doc.ocr_confidence}, "
                    f"ثقة الاستخراج: {doc.extraction_confidence}"
                ),
            )
            high_risk_count = sum(
                1 for f in risk_flags if f.get("severity") in ("high", "critical")
            )
            if high_risk_count > 0:
                notify_intelligence_processing_complete(
                    db,
                    event="risk_review_needed",
                    document_id=doc.id,
                    details=f"{high_risk_count} مخاطر مرتفعة/حرجة",
                )
            if matches:
                notify_intelligence_processing_complete(
                    db,
                    event="duplicate_review_needed",
                    document_id=doc.id,
                    details=f"{len(matches)} تكرارات محتملة",
                )
        except Exception:
            logger.exception("Notification failed for doc %s (non-fatal)", doc.id)

    except Exception as exc:
        logger.exception("Document processing failed for doc %s", doc.id)
        doc.processing_status = DocumentProcessingStatus.FAILED
        doc.error_message = str(exc)
        try:
            db.commit()
        except Exception:
            db.rollback()
