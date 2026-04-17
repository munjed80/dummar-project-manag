"""
Contract Duplicate Detection Service.

Detects potential duplicate or similar contracts using
practical signal matching: contract number, contractor name,
value, dates, and text similarity.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_intelligence import ContractDuplicate, DuplicateStatus

logger = logging.getLogger("dummar.duplicates")


@dataclass
class DuplicateMatch:
    """A potential duplicate match."""
    contract_id: int
    similarity_score: float
    reasons: List[str]


def _normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    # Remove common Arabic articles
    text = re.sub(r"\bال\b", "", text)
    return text.strip()


def _normalize_number(text: str) -> str:
    """Normalize contract number for comparison."""
    if not text:
        return ""
    return re.sub(r"[^a-zA-Z0-9]", "", text.lower())


def _text_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity (Jaccard)."""
    if not a or not b:
        return 0.0
    words_a = set(_normalize_text(a).split())
    words_b = set(_normalize_text(b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 0.0


def find_duplicates(
    db: Session,
    contract_number: Optional[str] = None,
    contractor_name: Optional[str] = None,
    title: Optional[str] = None,
    contract_value: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    exclude_contract_id: Optional[int] = None,
) -> List[DuplicateMatch]:
    """
    Find potential duplicate contracts in the database.
    
    Returns a list of DuplicateMatch objects, each with a
    similarity score and reasons for the match.
    """
    matches: Dict[int, DuplicateMatch] = {}

    all_contracts = db.query(Contract).all()

    for contract in all_contracts:
        if exclude_contract_id and contract.id == exclude_contract_id:
            continue

        reasons = []
        score = 0.0

        # 1. Exact contract number match (strongest signal)
        if contract_number and contract.contract_number:
            norm_a = _normalize_number(contract_number)
            norm_b = _normalize_number(contract.contract_number)
            if norm_a and norm_b and norm_a == norm_b:
                score += 0.5
                reasons.append(f"رقم عقد مطابق: {contract.contract_number}")

        # 2. Contractor name similarity
        if contractor_name and contract.contractor_name:
            name_sim = _text_similarity(contractor_name, contract.contractor_name)
            if name_sim > 0.5:
                score += 0.2 * name_sim
                reasons.append(
                    f"اسم مقاول مشابه: {contract.contractor_name} (تشابه: {name_sim:.0%})"
                )

        # 3. Title similarity
        if title and contract.title:
            title_sim = _text_similarity(title, contract.title)
            if title_sim > 0.4:
                score += 0.15 * title_sim
                reasons.append(
                    f"عنوان مشابه: {contract.title} (تشابه: {title_sim:.0%})"
                )

        # 4. Close contract value
        if contract_value and contract.contract_value:
            try:
                existing_value = float(contract.contract_value)
                if existing_value > 0:
                    value_ratio = min(contract_value, existing_value) / max(contract_value, existing_value)
                    if value_ratio > 0.9:
                        score += 0.1
                        reasons.append(
                            f"قيمة قريبة: {existing_value:,.2f} (تطابق: {value_ratio:.0%})"
                        )
            except (ValueError, TypeError):
                pass

        # 5. Overlapping dates
        if start_date and end_date and contract.start_date and contract.end_date:
            try:
                from datetime import datetime

                # Parse dates
                def parse_date(d):
                    if isinstance(d, str):
                        return datetime.strptime(d[:10], "%Y-%m-%d").date()
                    return d

                s1 = parse_date(start_date)
                e1 = parse_date(end_date)
                s2 = contract.start_date
                e2 = contract.end_date

                # Check overlap
                if s1 <= e2 and s2 <= e1:
                    overlap_days = (min(e1, e2) - max(s1, s2)).days
                    total_days = max((e1 - s1).days, (e2 - s2).days, 1)
                    overlap_ratio = overlap_days / total_days
                    if overlap_ratio > 0.5:
                        score += 0.05
                        reasons.append(f"تداخل زمني ({overlap_ratio:.0%})")
            except (ValueError, TypeError):
                pass

        # Only include if score is above threshold
        if score >= 0.15 and reasons:
            matches[contract.id] = DuplicateMatch(
                contract_id=contract.id,
                similarity_score=round(min(1.0, score), 3),
                reasons=reasons,
            )

    # Sort by score descending
    result = sorted(matches.values(), key=lambda m: m.similarity_score, reverse=True)
    return result[:20]  # Return top 20 matches


def save_duplicate_records(
    db: Session,
    document_id: Optional[int],
    matches: List[DuplicateMatch],
    contract_id_a: Optional[int] = None,
) -> List[ContractDuplicate]:
    """Save duplicate detection results to the database."""
    records = []
    for match in matches:
        record = ContractDuplicate(
            document_id=document_id,
            contract_id_a=contract_id_a,
            contract_id_b=match.contract_id,
            similarity_score=match.similarity_score,
            match_reasons=json.dumps(match.reasons, ensure_ascii=False),
            status=DuplicateStatus.PENDING,
        )
        db.add(record)
        records.append(record)
    db.commit()
    for r in records:
        db.refresh(r)
    return records
