"""
Contract Risk Analysis Service.

Identifies potential risks and issues in contracts.
Flags are indicators/warnings, not legal conclusions.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_intelligence import ContractRiskFlag, RiskSeverity

logger = logging.getLogger("dummar.risk")


@dataclass
class RiskFlag:
    """A single risk indicator."""
    risk_type: str
    severity: str  # low, medium, high, critical
    description: str
    details: Optional[str] = None


def analyze_contract_risks(
    contract: Optional[Contract] = None,
    extracted_fields: Optional[Dict[str, Any]] = None,
    ocr_text: Optional[str] = None,
) -> List[RiskFlag]:
    """
    Analyze a contract for potential risk indicators.
    
    Can analyze either an existing Contract object or extracted fields
    from a document being processed.
    
    Returns a list of RiskFlag objects.
    """
    flags: List[RiskFlag] = []

    if contract:
        flags.extend(_analyze_contract_object(contract))
    if extracted_fields is not None:
        flags.extend(_analyze_extracted_fields(extracted_fields))
    if ocr_text is not None:
        flags.extend(_analyze_text_quality(ocr_text))

    return flags


def _analyze_contract_object(contract: Contract) -> List[RiskFlag]:
    """Analyze an existing contract record for risks."""
    flags = []
    today = date.today()

    # Missing contract number
    if not contract.contract_number or not contract.contract_number.strip():
        flags.append(RiskFlag(
            risk_type="missing_contract_number",
            severity="high",
            description="رقم العقد مفقود",
            details="لم يتم تحديد رقم للعقد — مطلوب للتتبع والتوثيق",
        ))

    # Missing contractor name
    if not contract.contractor_name or not contract.contractor_name.strip():
        flags.append(RiskFlag(
            risk_type="missing_contractor",
            severity="high",
            description="اسم المقاول مفقود",
            details="لم يتم تحديد اسم المقاول أو الشركة",
        ))

    # Missing dates
    if not contract.start_date:
        flags.append(RiskFlag(
            risk_type="missing_start_date",
            severity="medium",
            description="تاريخ البدء مفقود",
        ))

    if not contract.end_date:
        flags.append(RiskFlag(
            risk_type="missing_end_date",
            severity="medium",
            description="تاريخ الانتهاء مفقود",
        ))

    # End date before start date
    if contract.start_date and contract.end_date:
        if contract.end_date < contract.start_date:
            flags.append(RiskFlag(
                risk_type="invalid_dates",
                severity="critical",
                description="تاريخ الانتهاء قبل تاريخ البدء",
                details=f"البدء: {contract.start_date}, الانتهاء: {contract.end_date}",
            ))

    # Expired contract
    if contract.end_date and contract.end_date < today:
        if contract.status in ("active", "approved"):
            days_expired = (today - contract.end_date).days
            flags.append(RiskFlag(
                risk_type="expired_contract",
                severity="high",
                description="العقد منتهي الصلاحية",
                details=f"انتهى منذ {days_expired} يوم ({contract.end_date})",
            ))

    # Near expiry (within 30 days)
    if contract.end_date and contract.start_date:
        if contract.end_date > today:
            days_remaining = (contract.end_date - today).days
            if days_remaining <= 30 and contract.status in ("active",):
                flags.append(RiskFlag(
                    risk_type="near_expiry",
                    severity="medium",
                    description="العقد قريب من الانتهاء",
                    details=f"متبقي {days_remaining} يوم (ينتهي: {contract.end_date})",
                ))

    # Unusually high value
    if contract.contract_value:
        try:
            value = float(contract.contract_value)
            if value > 100_000_000:  # > 100M
                flags.append(RiskFlag(
                    risk_type="high_value",
                    severity="medium",
                    description="قيمة عقد مرتفعة جداً",
                    details=f"القيمة: {value:,.2f} — يُنصح بمراجعة إضافية",
                ))
            if value <= 0:
                flags.append(RiskFlag(
                    risk_type="zero_value",
                    severity="high",
                    description="قيمة العقد صفر أو سالبة",
                    details=f"القيمة: {value}",
                ))
        except (ValueError, TypeError):
            pass

    # Missing scope description
    if not contract.scope_description or len(contract.scope_description.strip()) < 10:
        flags.append(RiskFlag(
            risk_type="vague_scope",
            severity="medium",
            description="نطاق العمل قصير أو غامض",
            details="وصف نطاق العمل أقل من 10 أحرف — قد يكون غير كافٍ",
        ))

    return flags


def _analyze_extracted_fields(fields: Dict[str, Any]) -> List[RiskFlag]:
    """Analyze extracted fields for completeness and consistency."""
    flags = []

    required_fields = [
        ("contract_number", "رقم العقد"),
        ("title", "عنوان العقد"),
        ("contractor_name", "اسم المقاول"),
        ("contract_value", "قيمة العقد"),
        ("start_date", "تاريخ البدء"),
        ("end_date", "تاريخ الانتهاء"),
    ]

    missing_count = 0
    for field_key, field_label in required_fields:
        if not fields.get(field_key):
            missing_count += 1

    if missing_count > 0:
        severity = "low" if missing_count <= 2 else "medium" if missing_count <= 4 else "high"
        flags.append(RiskFlag(
            risk_type="incomplete_extraction",
            severity=severity,
            description=f"حقول مفقودة في الاستخراج ({missing_count} من {len(required_fields)})",
            details=f"عدد الحقول المفقودة: {missing_count}",
        ))

    # Date consistency
    start = fields.get("start_date", "")
    end = fields.get("end_date", "")
    if start and end:
        try:
            s = datetime.strptime(start[:10], "%Y-%m-%d").date()
            e = datetime.strptime(end[:10], "%Y-%m-%d").date()
            if e < s:
                flags.append(RiskFlag(
                    risk_type="invalid_extracted_dates",
                    severity="high",
                    description="تواريخ مستخرجة غير متسقة",
                    details=f"تاريخ الانتهاء ({end}) قبل تاريخ البدء ({start})",
                ))
        except (ValueError, TypeError):
            pass

    # Scope quality
    scope = fields.get("scope_summary", "")
    if scope and len(scope.strip()) < 20:
        flags.append(RiskFlag(
            risk_type="short_scope",
            severity="low",
            description="نطاق العمل المستخرج قصير جداً",
            details=f"طول النص: {len(scope.strip())} حرف",
        ))

    return flags


def _analyze_text_quality(text: str) -> List[RiskFlag]:
    """Analyze OCR text quality for potential issues."""
    flags = []

    if not text or not text.strip():
        flags.append(RiskFlag(
            risk_type="empty_ocr_text",
            severity="high",
            description="لم يتم استخراج أي نص",
            details="النص المستخرج فارغ — قد يكون الملف صورة أو ملف تالف",
        ))
        return flags

    # Very short text
    if len(text.strip()) < 50:
        flags.append(RiskFlag(
            risk_type="very_short_text",
            severity="medium",
            description="النص المستخرج قصير جداً",
            details=f"طول النص: {len(text.strip())} حرف — قد يكون الاستخراج غير مكتمل",
        ))

    return flags


def save_risk_flags(
    db: Session,
    flags: List[RiskFlag],
    document_id: Optional[int] = None,
    contract_id: Optional[int] = None,
) -> List[ContractRiskFlag]:
    """Save risk flags to the database."""
    records = []
    for flag in flags:
        record = ContractRiskFlag(
            document_id=document_id,
            contract_id=contract_id,
            risk_type=flag.risk_type,
            severity=RiskSeverity(flag.severity),
            description=flag.description,
            details=flag.details,
            is_resolved=False,
        )
        db.add(record)
        records.append(record)
    if records:
        db.commit()
        for r in records:
            db.refresh(r)
    return records
