"""
Location service — auto-assignment, proximity, and fuzzy-text helpers.

Provides:
- infer_location_id: attempts to determine the best Location for a complaint/task
  based on explicit location_id, area_id mapping, fuzzy text match, or coordinate
  proximity (Haversine).
- find_nearest_location: finds the closest Location by lat/lng using the Haversine
  formula for accurate great-circle distance.
- fuzzy_match_location: attempts to match a free-text location description to a
  Location record using simple text similarity.

Design:
- Returns None if confidence is low — never silently forces a wrong assignment.
- Caller can always override with an explicit location_id.
"""

import logging
import math
import re
import json
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models.location import Location, LocationType, LocationStatus, Area

logger = logging.getLogger("dummar.location_service")

# Maximum distance in meters to auto-assign by coordinates
_MAX_PROXIMITY_METERS = 550.0

# Minimum fuzzy-match score (0–1) to auto-assign by text
_MIN_FUZZY_SCORE = 0.6

# Earth's mean radius in meters
_EARTH_RADIUS_M = 6_371_000.0

_LOCATION_KEYWORDS = (
    "الجزيرة", "السوق", "الشارع", "الحي", "البناء", "المنطقة",
    "جزيره", "سوق", "شارع", "حي", "بناء", "منطقه",
)


@dataclass
class LocationMatchResult:
    location: Optional[Location]
    confidence: str  # high | medium | low | none
    score: float
    reason: str


# ─────────────────────────────────────────────────────────────
# Haversine distance
# ─────────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance between two points on Earth (in meters)
    using the Haversine formula.
    """
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_M * c


# ─────────────────────────────────────────────────────────────
# Fuzzy text matching helpers
# ─────────────────────────────────────────────────────────────

def _normalize_arabic(text: str) -> str:
    """Normalize Arabic text for comparison: remove diacritics, normalize alef/ya."""
    if not text:
        return ""
    # Remove Arabic diacritics (tashkeel)
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Normalize alef variants to plain alef
    text = re.sub(r'[إأآا]', 'ا', text)
    # Normalize ya/alef maqsura
    text = re.sub(r'[يى]', 'ي', text)
    # Normalize ta marbuta
    text = text.replace('ة', 'ه')
    # Strip extra whitespace
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text


def _text_similarity(a: str, b: str) -> float:
    """
    Simple trigram-based similarity score (0–1) between two strings.
    Adequate for matching location names — not a full NLP engine.
    """
    if not a or not b:
        return 0.0
    a_n = _normalize_arabic(a)
    b_n = _normalize_arabic(b)
    if a_n == b_n:
        return 1.0
    # Check substring containment (one contains the other)
    if a_n in b_n or b_n in a_n:
        return 0.85

    # Trigram overlap
    def _trigrams(s: str) -> set:
        return {s[i:i+3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}

    tg_a = _trigrams(a_n)
    tg_b = _trigrams(b_n)
    if not tg_a or not tg_b:
        return 0.0
    intersection = tg_a & tg_b
    union = tg_a | tg_b
    return len(intersection) / len(union) if union else 0.0


def _extract_location_terms(text: str) -> str:
    """Keep likely geographic terms to improve fuzzy recall on partial addresses."""
    text_n = _normalize_arabic(text or "")
    if not text_n:
        return ""
    parts = re.split(r"[،,;:|/\-]+|\s+", text_n)
    kept = [p for p in parts if p and (len(p) >= 3 or p in _LOCATION_KEYWORDS)]
    return " ".join(kept[:12])


def _location_aliases(loc: Location) -> list[str]:
    aliases: list[str] = []
    if loc.description:
        aliases.append(loc.description)
    if loc.metadata_json:
        try:
            data = json.loads(loc.metadata_json) if isinstance(loc.metadata_json, str) else loc.metadata_json
            if isinstance(data, dict):
                for key in ("aliases", "alternative_names", "alt_names", "keywords"):
                    raw = data.get(key)
                    if isinstance(raw, list):
                        aliases.extend([str(x) for x in raw if x])
                    elif isinstance(raw, str):
                        aliases.append(raw)
        except Exception:
            pass
    return aliases


def infer_location_from_address(
    db: Session,
    *,
    location_text: Optional[str] = None,
    detailed_address: Optional[str] = None,
) -> LocationMatchResult:
    """
    Infer a reference location from partially-structured Arabic text with
    confidence scoring.
    """
    source = " ".join(x for x in [location_text, detailed_address] if x and x.strip()).strip()
    if not source:
        return LocationMatchResult(location=None, confidence="none", score=0.0, reason="empty_text")

    source_norm = _normalize_arabic(source)
    source_terms = _extract_location_terms(source)
    candidates = db.query(Location).filter(Location.is_active == 1).all()
    if not candidates:
        return LocationMatchResult(location=None, confidence="none", score=0.0, reason="no_candidates")

    best: Optional[Location] = None
    best_score = 0.0
    best_reason = "no_match"

    for loc in candidates:
        name_n = _normalize_arabic(loc.name or "")
        code_n = _normalize_arabic(loc.code or "")
        score_name = _text_similarity(source_norm, name_n)
        score_terms = _text_similarity(source_terms, name_n) if source_terms else 0.0
        score_code = _text_similarity(source_norm, code_n) if code_n else 0.0
        score_alias = 0.0
        for alias in _location_aliases(loc):
            score_alias = max(score_alias, _text_similarity(source_norm, alias))

        keyword_bonus = 0.0
        if any(k in source_norm for k in _LOCATION_KEYWORDS):
            if any(k in name_n for k in _LOCATION_KEYWORDS):
                keyword_bonus = 0.05

        token_overlap = 0.0
        source_tokens = set(source_terms.split()) if source_terms else set()
        name_tokens = set(name_n.split()) if name_n else set()
        if source_tokens and name_tokens:
            common = source_tokens & name_tokens
            if common:
                token_overlap = min(0.88, 0.75 + (0.06 * len(common)))

        score = max(score_name, score_terms, score_code, score_alias, token_overlap) + keyword_bonus
        reason = "fuzzy"
        if score_name >= 0.99 or score_code >= 0.99:
            score = max(score, 1.0)
            reason = "exact"
        elif name_n and (name_n in source_norm or source_norm in name_n):
            score = max(score, 0.88)
            reason = "partial"
        elif score_alias >= 0.8:
            reason = "alias"

        if score > best_score:
            best = loc
            best_score = score
            best_reason = reason

    if not best:
        return LocationMatchResult(location=None, confidence="none", score=0.0, reason="no_match")

    if best_score >= 0.9:
        confidence = "high"
    elif best_score >= 0.72:
        confidence = "medium"
    elif best_score >= 0.56:
        confidence = "low"
    else:
        confidence = "none"

    if confidence in ("none", "low"):
        return LocationMatchResult(location=best, confidence="low", score=best_score, reason=best_reason)
    return LocationMatchResult(location=best, confidence=confidence, score=best_score, reason=best_reason)


def fuzzy_match_location(
    db: Session,
    text: str,
    min_score: float = _MIN_FUZZY_SCORE,
) -> Optional[Location]:
    """
    Find the best-matching active Location for a free-text description.
    Returns None if no match exceeds min_score.
    """
    if not text or not text.strip():
        return None

    candidates = (
        db.query(Location)
        .filter(Location.is_active == 1)
        .all()
    )
    best: Optional[Location] = None
    best_score = 0.0

    text_norm = _normalize_arabic(text)

    for loc in candidates:
        # Score against name
        score = _text_similarity(text, loc.name)
        # Also check against code
        code_score = _text_similarity(text_norm, loc.code.lower()) if loc.code else 0.0
        # Also check description
        desc_score = _text_similarity(text, loc.description) if loc.description else 0.0
        max_score = max(score, code_score, desc_score)

        if max_score > best_score:
            best_score = max_score
            best = loc

    if best and best_score >= min_score:
        logger.info("Fuzzy text match: '%s' → Location id=%d (%s) score=%.2f",
                    text[:30], best.id, best.name, best_score)
        return best

    return None


# ─────────────────────────────────────────────────────────────
# Main inference
# ─────────────────────────────────────────────────────────────

def infer_location_id(
    db: Session,
    *,
    explicit_location_id: Optional[int] = None,
    area_id: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    location_text: Optional[str] = None,
) -> Optional[int]:
    """
    Try to determine the correct location_id using available data.

    Priority:
    1. If explicit_location_id is given and valid → use it.
    2. If area_id is given → find the Location migrated from that area.
    3. If coordinates are given → find nearest active Location within threshold (Haversine).
    4. If location_text is given → attempt fuzzy text match.
    5. Otherwise → return None (manual assignment needed).
    """
    # 1. Explicit location
    if explicit_location_id is not None:
        loc = (
            db.query(Location)
            .filter(Location.id == explicit_location_id, Location.is_active == 1)
            .first()
        )
        if loc:
            return loc.id
        logger.warning("Explicit location_id=%d not found or inactive", explicit_location_id)
        return None

    # 2. Area mapping — look for Location with code = LOC-{area.code}
    if area_id is not None:
        area = db.query(Area).filter(Area.id == area_id).first()
        if area:
            mapped_code = f"LOC-{area.code}"
            mapped = (
                db.query(Location)
                .filter(Location.code == mapped_code, Location.is_active == 1)
                .first()
            )
            if mapped:
                logger.info("Area id=%d → mapped to Location id=%d",
                            area_id, mapped.id)
                return mapped.id

    # 3. Coordinate proximity (Haversine)
    if latitude is not None and longitude is not None:
        nearest = find_nearest_location(db, latitude, longitude)
        if nearest:
            logger.info("Coordinate proximity match → Location id=%d (%s)",
                        nearest.id, nearest.name)
            return nearest.id

    # 4. Fuzzy text match
    if location_text:
        matched = fuzzy_match_location(db, location_text)
        if matched:
            return matched.id

    return None


def find_nearest_location(
    db: Session,
    latitude: float,
    longitude: float,
    max_distance_m: float = _MAX_PROXIMITY_METERS,
) -> Optional[Location]:
    """
    Find the nearest active Location with coordinates within max_distance_m meters.

    Uses the Haversine formula for accurate great-circle distance.
    Returns None if no location is close enough.
    """
    candidates = (
        db.query(Location)
        .filter(
            Location.is_active == 1,
            Location.latitude.isnot(None),
            Location.longitude.isnot(None),
        )
        .all()
    )

    best: Optional[Location] = None
    best_dist = float("inf")

    for loc in candidates:
        dist = _haversine_m(latitude, longitude, loc.latitude, loc.longitude)
        if dist < best_dist:
            best_dist = dist
            best = loc

    if best and best_dist <= max_distance_m:
        return best

    return None
