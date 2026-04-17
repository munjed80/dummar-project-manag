"""
Contract Classification Service.

Classifies contracts by type based on extracted fields and text content.
Uses keyword matching and field analysis — no external AI dependency.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger("dummar.classification")


@dataclass
class ClassificationResult:
    suggested_type: str
    confidence: float
    reason: str


# Classification keywords mapped to contract types
_CLASSIFICATION_RULES = {
    "maintenance": {
        "keywords_ar": ["صيانة", "إصلاح", "ترميم", "تأهيل", "صيانة دورية"],
        "keywords_en": ["maintenance", "repair", "rehabilitation", "overhaul"],
        "weight": 1.0,
    },
    "cleaning": {
        "keywords_ar": ["تنظيف", "نظافة", "كنس", "غسيل", "إزالة نفايات"],
        "keywords_en": ["cleaning", "waste", "sanitation", "janitorial"],
        "weight": 1.0,
    },
    "construction": {
        "keywords_ar": ["إنشاء", "بناء", "تشييد", "إعمار", "إنشائي", "هيكل"],
        "keywords_en": ["construction", "building", "erection", "structural"],
        "weight": 1.0,
    },
    "roads": {
        "keywords_ar": ["طرق", "رصف", "أرصفة", "طريق", "شارع", "زفت"],
        "keywords_en": ["roads", "paving", "asphalt", "sidewalk", "pavement"],
        "weight": 1.0,
    },
    "lighting": {
        "keywords_ar": ["إنارة", "إضاءة", "كهرباء", "أعمدة إنارة", "كهربائي"],
        "keywords_en": ["lighting", "electrical", "illumination", "lamp"],
        "weight": 1.0,
    },
    "supply": {
        "keywords_ar": ["توريد", "تجهيز", "شراء", "مواد", "معدات"],
        "keywords_en": ["supply", "procurement", "materials", "equipment"],
        "weight": 0.9,
    },
    "consulting": {
        "keywords_ar": ["استشارات", "استشاري", "دراسة", "تصميم", "إشراف"],
        "keywords_en": ["consulting", "consultancy", "study", "design", "supervision"],
        "weight": 0.9,
    },
    "services": {
        "keywords_ar": ["خدمات", "تشغيل", "حراسة", "أمن", "نقل"],
        "keywords_en": ["services", "operation", "security", "guard", "transport"],
        "weight": 0.8,
    },
    "other": {
        "keywords_ar": [],
        "keywords_en": [],
        "weight": 0.1,
    },
}


def classify_contract(
    text: Optional[str] = None,
    extracted_fields: Optional[Dict[str, Any]] = None,
) -> ClassificationResult:
    """
    Classify a contract based on text and/or extracted fields.
    Returns the most likely contract type with confidence and reason.
    """
    if not text and not extracted_fields:
        return ClassificationResult(
            suggested_type="other",
            confidence=0.0,
            reason="No text or fields provided for classification",
        )

    scores: Dict[str, float] = {}
    reasons: Dict[str, list] = {}

    combined_text = (text or "").lower()

    # Add extracted fields to text for analysis
    if extracted_fields:
        for key, value in extracted_fields.items():
            if isinstance(value, str):
                combined_text += " " + value.lower()

        # Check if contract_type was already extracted
        if extracted_fields.get("contract_type"):
            preset = extracted_fields["contract_type"].lower()
            for ctype in _CLASSIFICATION_RULES:
                if ctype in preset or preset in ctype:
                    scores[ctype] = scores.get(ctype, 0) + 5.0
                    reasons.setdefault(ctype, []).append(f"Extracted type field: {preset}")

    # Score each type based on keyword matches
    for ctype, rules in _CLASSIFICATION_RULES.items():
        if ctype == "other":
            continue

        for kw in rules["keywords_ar"] + rules["keywords_en"]:
            count = combined_text.count(kw.lower())
            if count > 0:
                score = count * rules["weight"]
                scores[ctype] = scores.get(ctype, 0) + score
                reasons.setdefault(ctype, []).append(f"Keyword '{kw}' found {count}x")

    if not scores:
        return ClassificationResult(
            suggested_type="other",
            confidence=0.3,
            reason="No matching keywords found — defaulting to 'other'",
        )

    # Normalize scores
    max_score = max(scores.values())
    total_score = sum(scores.values())

    best_type = max(scores, key=scores.get)
    confidence = round(min(0.95, max_score / max(total_score, 1) * 0.9 + 0.1), 3)

    reason_text = f"Classification: {best_type} (score: {max_score:.1f}). "
    reason_text += "Matched: " + "; ".join(reasons.get(best_type, [])[:5])

    return ClassificationResult(
        suggested_type=best_type,
        confidence=confidence,
        reason=reason_text,
    )
