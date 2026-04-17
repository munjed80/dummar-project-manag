"""
Location service — auto-assignment and proximity helpers.

Provides:
- infer_location_id: attempts to determine the best Location for a complaint/task
  based on explicit location_id, area_id mapping, or coordinate proximity.
- find_nearest_location: finds the closest Location by lat/lng (simple Euclidean
  distance — good enough for same-city operations; not a GIS replacement).

Design:
- Returns None if confidence is low — never silently forces a wrong assignment.
- Caller can always override with an explicit location_id.
"""

import logging
import math
from typing import Optional

from sqlalchemy.orm import Session

from app.models.location import Location, LocationType, LocationStatus, Area

logger = logging.getLogger("dummar.location_service")

# Maximum distance (in degrees, ~0.005 ≈ 550 m in Dummar latitude) to auto-assign
_MAX_PROXIMITY_DEGREES = 0.005


def infer_location_id(
    db: Session,
    *,
    explicit_location_id: Optional[int] = None,
    area_id: Optional[int] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Optional[int]:
    """
    Try to determine the correct location_id using available data.

    Priority:
    1. If explicit_location_id is given and valid → use it.
    2. If area_id is given → find the Location migrated from that area.
    3. If coordinates are given → find nearest active Location within threshold.
    4. Otherwise → return None (manual assignment needed).
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
                logger.info("Area id=%d → mapped to Location id=%d (code=%s)",
                            area_id, mapped.id, mapped_code)
                return mapped.id

    # 3. Coordinate proximity
    if latitude is not None and longitude is not None:
        nearest = find_nearest_location(db, latitude, longitude)
        if nearest:
            logger.info("Coordinates (%.5f, %.5f) → nearest Location id=%d (%s)",
                        latitude, longitude, nearest.id, nearest.name)
            return nearest.id

    return None


def find_nearest_location(
    db: Session,
    latitude: float,
    longitude: float,
    max_distance: float = _MAX_PROXIMITY_DEGREES,
) -> Optional[Location]:
    """
    Find the nearest active Location with coordinates within max_distance.

    Uses simple Euclidean distance in degrees — adequate for intra-city use.
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
        dist = math.sqrt(
            (loc.latitude - latitude) ** 2 + (loc.longitude - longitude) ** 2
        )
        if dist < best_dist:
            best_dist = dist
            best = loc

    if best and best_dist <= max_distance:
        return best

    return None
