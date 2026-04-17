"""
Contract Summary Generation Service.

Generates concise operational summaries for contracts based on
extracted fields and text content. Designed to help managers
quickly understand a contract's key details.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("dummar.summary")


_TYPE_LABELS = {
    "maintenance": "صيانة",
    "cleaning": "تنظيف",
    "construction": "إنشاء",
    "roads": "طرق",
    "lighting": "إنارة",
    "supply": "توريد",
    "consulting": "استشارات",
    "services": "خدمات",
    "other": "أخرى",
}


def generate_summary(
    extracted_fields: Optional[Dict[str, Any]] = None,
    ocr_text: Optional[str] = None,
    contract_type: Optional[str] = None,
) -> str:
    """
    Generate a concise operational summary for a contract.
    
    Returns a human-readable Arabic summary string.
    """
    if not extracted_fields and not ocr_text:
        return "لا تتوفر بيانات كافية لإنشاء ملخص."

    fields = extracted_fields or {}
    parts = []

    # Title / subject
    title = fields.get("title", "")
    if title:
        parts.append(f"العقد: {title}")

    # Contractor
    contractor = fields.get("contractor_name", "")
    if contractor:
        parts.append(f"المقاول/الشركة: {contractor}")

    # Contract type
    ctype = contract_type or fields.get("contract_type", "")
    if ctype:
        type_label = _TYPE_LABELS.get(ctype, ctype)
        parts.append(f"نوع العقد: {type_label}")

    # Value
    value = fields.get("contract_value")
    if value is not None:
        currency = fields.get("currency", "ل.س")
        try:
            formatted_value = f"{float(value):,.2f}"
            parts.append(f"القيمة: {formatted_value} {currency}")
        except (ValueError, TypeError):
            parts.append(f"القيمة: {value}")

    # Dates
    start = fields.get("start_date", "")
    end = fields.get("end_date", "")
    if start and end:
        parts.append(f"الفترة: من {start} إلى {end}")
    elif start:
        parts.append(f"تاريخ البدء: {start}")
    elif end:
        parts.append(f"تاريخ الانتهاء: {end}")

    # Duration
    duration = fields.get("execution_duration_days")
    if duration:
        parts.append(f"مدة التنفيذ: {duration} يوم")

    # Scope
    scope = fields.get("scope_summary", "")
    if scope:
        # Truncate scope for summary
        scope_short = scope[:300] + ("..." if len(scope) > 300 else "")
        parts.append(f"نطاق العمل: {scope_short}")

    # Locations
    locations = fields.get("covered_locations", "")
    if locations:
        parts.append(f"المواقع: {locations}")

    # Contract number
    contract_number = fields.get("contract_number", "")
    if contract_number:
        parts.append(f"رقم العقد: {contract_number}")

    if not parts:
        # Fallback: use OCR text snippet
        if ocr_text and len(ocr_text.strip()) > 20:
            snippet = ocr_text.strip()[:500]
            return f"ملخص أولي (من النص المستخرج):\n{snippet}"
        return "لا تتوفر بيانات كافية لإنشاء ملخص تفصيلي."

    summary = "\n".join(parts)
    return summary
