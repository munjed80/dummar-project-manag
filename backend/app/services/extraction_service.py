"""
Contract Field Extraction Service.

Extracts structured fields from OCR text or raw contract text.
Uses pattern matching, keyword detection, and heuristic rules.
No external AI API dependency — designed to be practical and honest
about extraction confidence.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger("dummar.extraction")


@dataclass
class ExtractionResult:
    """Result of field extraction from text."""
    fields: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)
    success: bool = False


# Common Arabic/English patterns (refined for mixed-language + OCR noise)
_DATE_PATTERNS = [
    # yyyy-mm-dd or yyyy/mm/dd
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    # dd-mm-yyyy or dd/mm/yyyy
    r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
    # dd.mm.yyyy (common in Arabic documents)
    r"(\d{1,2}\.\d{1,2}\.\d{4})",
    # yyyy.mm.dd
    r"(\d{4}\.\d{1,2}\.\d{1,2})",
]

_CURRENCY_PATTERNS = [
    # Arabic currency variants (ل.س with possible OCR noise like spaces)
    r"([\d,\s]+(?:\.\d{1,2})?)\s*(?:ل[\.\s]*س|ليرة\s*سورية|ليرة|SYP|syp|ل\.س\.)",
    r"([\d,\s]+(?:\.\d{1,2})?)\s*(?:USD|دولار\s*أمريكي|دولار|\$)",
    r"([\d,\s]+(?:\.\d{1,2})?)\s*(?:EUR|يورو|€)",
    # Reversed: currency then number
    r"(?:ل[\.\s]*س|ليرة|SYP)\s*([\d,\s]+(?:\.\d{1,2})?)",
    r"(?:\$|USD|دولار)\s*([\d,\s]+(?:\.\d{1,2})?)",
]

_CONTRACT_NUMBER_PATTERNS = [
    # Mixed Arabic/English labels: "رقم العقد" / "contract no" / "عقد رقم"
    r"(?:رقم\s*العقد|عقد\s*رقم|contract\s*(?:no|number|#|num))\s*[:\-–—]?\s*([A-Za-z0-9\u0660-\u0669\-/\.]+)",
    # Standalone pattern with Arabic label
    r"(?:رقم)\s*[:\-–—]?\s*([A-Za-z0-9\u0660-\u0669\-/\.]{3,25})",
    # Pattern like "No. XXX" or "رقم: XXX" (OCR may add spaces)
    r"(?:No\.|no\.)\s*([A-Za-z0-9\-/\.]{3,25})",
    # Hyphenated contract patterns like "2024-MAINT-001"
    r"\b(\d{4}[-/][A-Z]{2,10}[-/]\d{2,5})\b",
]

_CONTRACTOR_PATTERNS = [
    # Arabic + English mixed labels with flexible punctuation
    r"(?:المقاول|الشركة|المتعهد|الجهة\s*المنفذة|المقاول\s*الرئيسي|contractor|company|vendor|supplier)\s*[:\-–—]?\s*(.+?)(?:\n|$)",
    r"(?:اسم\s*المقاول|اسم\s*الشركة)\s*[:\-–—]?\s*(.+?)(?:\n|$)",
    r"(?:بين|between)\s+.*?(?:و|and)\s+(.+?)(?:\n|$)",
    # Company suffix patterns
    r"((?:شركة|مؤسسة|مكتب)\s+[^\n,;]{3,80})",
]

_DURATION_PATTERNS = [
    r"(\d+)\s*(?:يوم|أيام|days?)",
    r"(\d+)\s*(?:شهر|أشهر|months?)",
    r"(\d+)\s*(?:سنة|سنوات|years?)",
    r"(\d+)\s*(?:أسبوع|أسابيع|weeks?)",
]

_TYPE_KEYWORDS = {
    "maintenance": ["صيانة", "maintenance", "إصلاح", "repair", "ترميم", "تأهيل"],
    "cleaning": ["تنظيف", "نظافة", "cleaning", "كنس", "إزالة نفايات"],
    "construction": ["إنشاء", "بناء", "construction", "تشييد", "إعمار", "تعمير"],
    "roads": ["طرق", "roads", "رصف", "أرصفة", "paving", "جسور", "طريق"],
    "lighting": ["إنارة", "إضاءة", "lighting", "كهرباء", "electrical", "كهربائي"],
    "supply": ["توريد", "supply", "تجهيز", "procurement", "شراء", "مشتريات"],
    "consulting": ["استشار", "consulting", "دراس", "study", "تصميم", "إشراف"],
    "services": ["خدمات", "services", "تشغيل", "operation", "حراسة", "أمن"],
}


def _clean_ocr_noise(text: str) -> str:
    """Remove common OCR noise while preserving meaningful content."""
    if not text:
        return text
    # Normalize Arabic diacritics (tashkeel)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Normalize multiple spaces
    text = re.sub(r' {2,}', ' ', text)
    # Normalize line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove isolated single characters that are likely noise (but keep Arabic)
    text = re.sub(r'(?<= )[^\w\u0600-\u06FF](?= )', '', text)
    return text


def extract_fields(text: str) -> ExtractionResult:
    """
    Extract structured contract fields from text.
    Returns ExtractionResult with fields, confidence, and notes.
    """
    if not text or not text.strip():
        return ExtractionResult(
            fields={},
            confidence=0.0,
            notes=["No text provided for extraction"],
            success=False,
        )

    # Clean OCR noise before extraction
    cleaned_text = _clean_ocr_noise(text)

    fields: Dict[str, Any] = {}
    notes: List[str] = []
    extracted_count = 0
    total_fields = 10  # number of fields we try to extract

    # 1. Contract number
    contract_number = _extract_contract_number(cleaned_text)
    if contract_number:
        fields["contract_number"] = contract_number
        extracted_count += 1
    else:
        notes.append("Contract number not found in text")

    # 2. Dates
    dates = _extract_dates(cleaned_text)
    if dates:
        if len(dates) >= 1:
            fields["start_date"] = dates[0]
            extracted_count += 1
        if len(dates) >= 2:
            fields["end_date"] = dates[1]
            extracted_count += 1
        if len(dates) > 2:
            fields["key_dates"] = dates[2:]
    else:
        notes.append("No dates found in text")

    # 3. Contract value / currency
    value_info = _extract_value(cleaned_text)
    if value_info:
        fields["contract_value"] = value_info["value"]
        if value_info.get("currency"):
            fields["currency"] = value_info["currency"]
        extracted_count += 1
    else:
        notes.append("Contract value not found in text")

    # 4. Contractor name
    contractor = _extract_contractor(cleaned_text)
    if contractor:
        fields["contractor_name"] = contractor
        extracted_count += 1
    else:
        notes.append("Contractor name not found in text")

    # 5. Duration
    duration = _extract_duration(cleaned_text)
    if duration:
        fields["execution_duration_days"] = duration
        extracted_count += 1

    # 6. Title (first meaningful line or heading)
    title = _extract_title(cleaned_text)
    if title:
        fields["title"] = title
        extracted_count += 1

    # 7. Scope summary (extract relevant paragraphs)
    scope = _extract_scope(cleaned_text)
    if scope:
        fields["scope_summary"] = scope
        extracted_count += 1

    # 8. Contract type (classify from content)
    contract_type = _classify_type_from_text(cleaned_text)
    if contract_type:
        fields["contract_type"] = contract_type
        extracted_count += 1

    # 9. Locations/areas
    locations = _extract_locations(cleaned_text)
    if locations:
        fields["covered_locations"] = locations
        extracted_count += 1

    # 10. Referenced attachments
    attachments = _extract_attachments(cleaned_text)
    if attachments:
        fields["referenced_attachments"] = attachments
        extracted_count += 1

    confidence = round(extracted_count / total_fields, 3) if total_fields > 0 else 0.0

    return ExtractionResult(
        fields=fields,
        confidence=confidence,
        notes=notes,
        success=extracted_count > 0,
    )


def _extract_contract_number(text: str) -> Optional[str]:
    for pattern in _CONTRACT_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def _extract_dates(text: str) -> List[str]:
    dates = []
    for pattern in _DATE_PATTERNS:
        for match in re.finditer(pattern, text):
            date_str = match.group(1)
            # Normalize to yyyy-mm-dd
            normalized = _normalize_date(date_str)
            if normalized and normalized not in dates:
                dates.append(normalized)
    return sorted(dates)[:5]  # Return up to 5 dates, sorted


_TWO_DIGIT_YEAR_CUTOFF = 50  # years below this are 2000s, above are 1900s


def _normalize_date(date_str: str) -> Optional[str]:
    """Try to parse and normalize a date string to yyyy-mm-dd."""
    date_str = date_str.replace("/", "-").replace(".", "-")
    parts = date_str.split("-")
    if len(parts) != 3:
        return None
    try:
        # If first part is 4 digits, it's yyyy-mm-dd
        if len(parts[0]) == 4:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        else:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        # Handle 2-digit years
        if y < 100:
            y += 2000 if y < _TWO_DIGIT_YEAR_CUTOFF else 1900
        if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, IndexError):
        pass
    return None


def _extract_value(text: str) -> Optional[Dict[str, Any]]:
    for pattern in _CURRENCY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(",", "").replace(" ", "")
            try:
                value = float(value_str)
                # Determine currency
                full_match = match.group(0)
                currency = "SYP"
                if any(c in full_match for c in ["USD", "دولار", "$"]):
                    currency = "USD"
                elif any(c in full_match for c in ["EUR", "يورو", "€"]):
                    currency = "EUR"
                return {"value": value, "currency": currency}
            except ValueError:
                continue

    # Fallback: find large numbers that might be values
    large_numbers = re.findall(r"([\d,\s]{5,}(?:\.\d{1,2})?)", text)
    if large_numbers:
        try:
            value = float(large_numbers[0].replace(",", "").replace(" ", ""))
            if value >= 1000:
                return {"value": value, "currency": None}
        except ValueError:
            pass

    return None


def _extract_contractor(text: str) -> Optional[str]:
    for pattern in _CONTRACTOR_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            name = match.group(1).strip()
            # Clean up: remove trailing punctuation, limit length
            name = re.sub(r"[.،:;؛\-–—]+$", "", name).strip()
            # Remove leading/trailing quotes
            name = name.strip('"\'«»""')
            if 3 <= len(name) <= 200:
                return name
    return None


def _extract_duration(text: str) -> Optional[int]:
    for pattern in _DURATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            full = match.group(0)
            if any(w in full for w in ["شهر", "أشهر", "month"]):
                return value * 30
            elif any(w in full for w in ["سنة", "سنوات", "year"]):
                return value * 365
            elif any(w in full for w in ["أسبوع", "أسابيع", "week"]):
                return value * 7
            else:
                return value
    return None


def _extract_title(text: str) -> Optional[str]:
    """Extract title from first meaningful line or contract heading."""
    lines = text.strip().split("\n")
    # First pass: look for lines with contract-related keywords
    for line in lines[:15]:
        line = line.strip()
        if len(line) > 10 and not line.startswith("#"):
            if any(kw in line.lower() for kw in ["عقد", "contract", "اتفاق", "agreement", "اتفاقية", "مذكرة"]):
                # Clean OCR artifacts from title
                title = re.sub(r'[_|]+', '', line).strip()
                if len(title) > 5:
                    return title[:200]
    # Second pass: first non-empty meaningful line (skip very short noise)
    for line in lines[:10]:
        line = line.strip()
        if len(line) > 8 and not re.match(r'^[\d\s\-\.]+$', line):
            title = re.sub(r'[_|]+', '', line).strip()
            if len(title) > 5:
                return title[:200]
    return None


def _extract_scope(text: str) -> Optional[str]:
    """Extract scope/description section."""
    scope_headers = [
        r"(?:نطاق العمل|نطاق الأعمال|scope of work|scope)",
        r"(?:وصف الأعمال|description of works?|وصف المشروع)",
        r"(?:الأعمال المطلوبة|required works?)",
    ]
    for pattern in scope_headers:
        match = re.search(pattern + r"\s*[:\-]?\s*(.+?)(?:\n\n|\n[A-Z]|\n\d+\.)", text, re.IGNORECASE | re.DOTALL)
        if match:
            scope = match.group(1).strip()
            if len(scope) > 20:
                return scope[:2000]

    # Fallback: return a chunk of text
    if len(text) > 100:
        return text[:500] + "..."
    return None


def _classify_type_from_text(text: str) -> Optional[str]:
    """Classify contract type based on keyword frequency."""
    text_lower = text.lower()
    scores = {}
    for ctype, keywords in _TYPE_KEYWORDS.items():
        score = sum(text_lower.count(kw.lower()) for kw in keywords)
        if score > 0:
            scores[ctype] = score
    if scores:
        return max(scores, key=scores.get)
    return None


def _extract_locations(text: str) -> Optional[str]:
    """Extract location references."""
    location_patterns = [
        r"(?:جزيرة|منطقة|حي|island|area|zone)\s+([^\n,;]{3,50})",
    ]
    locations = []
    for pattern in location_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            loc = match.group(1).strip()
            if loc not in locations:
                locations.append(loc)
    return ", ".join(locations) if locations else None


def _extract_attachments(text: str) -> Optional[str]:
    """Extract referenced attachment/appendix names."""
    attachment_patterns = [
        r"(?:ملحق|مرفق|appendix|attachment|annex)\s*(?:\d+|[A-Za-z])?[:\-]?\s*([^\n]{5,100})",
    ]
    attachments = []
    for pattern in attachment_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            att = match.group(1).strip() if match.lastindex else match.group(0).strip()
            if att not in attachments:
                attachments.append(att)
    return "; ".join(attachments) if attachments else None


def fields_to_json(fields: Dict[str, Any]) -> str:
    """Serialize extracted fields to JSON string for DB storage."""
    return json.dumps(fields, ensure_ascii=False, default=str)


def fields_from_json(json_str: Optional[str]) -> Dict[str, Any]:
    """Deserialize extracted fields from JSON string."""
    if not json_str:
        return {}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {}
