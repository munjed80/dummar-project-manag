"""
Area → Location migration script.

Migrates legacy Area/Building/Street records into the unified Location hierarchy.
Non-destructive: keeps legacy tables intact. Idempotent: safe to run multiple times.

Usage:
    cd backend
    python -m app.scripts.migrate_areas_to_locations
"""

import logging
import sys
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.database import SessionLocal
from app.models.location import (
    Area,
    Building,
    Location,
    LocationStatus,
    LocationType,
    Street,
)
from app.models.complaint import Complaint
from app.models.task import Task

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Code generators
# ---------------------------------------------------------------------------

def area_code(area: Area) -> str:
    """LOC-{area.code}"""
    return f"LOC-{area.code}"


def building_code(area: Area, building: Building) -> str:
    """BLD-{area.code}-{building.building_number or building.id}"""
    number = building.building_number if building.building_number else str(building.id)
    return f"BLD-{area.code}-{number}"


def street_code(street: Street) -> str:
    """STR-{street.code or street.id}"""
    code = street.code if street.code else str(street.id)
    return f"STR-{code}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_location(db, code: str, defaults: dict) -> tuple[Location, bool]:
    """Return (location, created). Idempotent – skips if code already exists."""
    existing = db.query(Location).filter(Location.code == code).first()
    if existing:
        return existing, False
    loc = Location(code=code, **defaults)
    db.add(loc)
    db.flush()  # populate loc.id for later FK references
    return loc, True


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

def migrate_areas(db) -> dict[int, int]:
    """Step 1: Area → Location (type=island). Returns {area.id: location.id}."""
    mapping: dict[int, int] = {}
    areas = db.query(Area).order_by(Area.id).all()
    logger.info("Found %d Area record(s) to migrate.", len(areas))

    for area in areas:
        code = area_code(area)
        loc, created = _get_or_create_location(db, code, {
            "name": area.name,
            "location_type": LocationType.ISLAND,
            "status": LocationStatus.ACTIVE,
            "description": area.description or "",
            "is_active": 1,
        })
        mapping[area.id] = loc.id
        if created:
            logger.info("  Created island Location id=%d code=%s from Area id=%d (%s)",
                        loc.id, code, area.id, area.name)
        else:
            logger.info("  Skipped (already exists) code=%s → Location id=%d", code, loc.id)

    return mapping


def migrate_buildings(db, area_mapping: dict[int, int]) -> int:
    """Step 2: Building → Location (type=building), parent = island location."""
    buildings = db.query(Building).order_by(Building.id).all()
    logger.info("Found %d Building record(s) to migrate.", len(buildings))
    created_count = 0

    for bldg in buildings:
        area = db.query(Area).filter(Area.id == bldg.area_id).first()
        if area is None:
            logger.warning("  Building id=%d references missing Area id=%s – skipped.",
                           bldg.id, bldg.area_id)
            continue

        parent_id = area_mapping.get(bldg.area_id)
        code = building_code(area, bldg)
        loc, created = _get_or_create_location(db, code, {
            "name": bldg.name,
            "location_type": LocationType.BUILDING,
            "parent_id": parent_id,
            "status": LocationStatus.ACTIVE,
            "is_active": 1,
        })
        if created:
            created_count += 1
            logger.info("  Created building Location id=%d code=%s (parent island id=%d) from Building id=%d",
                        loc.id, code, parent_id, bldg.id)
        else:
            logger.info("  Skipped (already exists) code=%s → Location id=%d", code, loc.id)

    return created_count


def migrate_streets(db) -> int:
    """Step 3: Street → Location (type=street), no parent."""
    streets = db.query(Street).order_by(Street.id).all()
    logger.info("Found %d Street record(s) to migrate.", len(streets))
    created_count = 0

    for st in streets:
        code = street_code(st)
        loc, created = _get_or_create_location(db, code, {
            "name": st.name,
            "location_type": LocationType.STREET,
            "status": LocationStatus.ACTIVE,
            "is_active": 1,
        })
        if created:
            created_count += 1
            logger.info("  Created street Location id=%d code=%s from Street id=%d (%s)",
                        loc.id, code, st.id, st.name)
        else:
            logger.info("  Skipped (already exists) code=%s → Location id=%d", code, loc.id)

    return created_count


def backfill_complaints(db, area_mapping: dict[int, int]) -> int:
    """Step 4: Set Complaint.location_id where area_id is mapped and location_id is NULL."""
    updated = 0
    for legacy_area_id, new_location_id in area_mapping.items():
        count = (
            db.query(Complaint)
            .filter(
                Complaint.area_id == legacy_area_id,
                Complaint.location_id.is_(None),
            )
            .update({"location_id": new_location_id}, synchronize_session="fetch")
        )
        if count:
            logger.info("  Linked %d Complaint(s) with area_id=%d → location_id=%d",
                        count, legacy_area_id, new_location_id)
            updated += count
    return updated


def backfill_tasks(db, area_mapping: dict[int, int]) -> int:
    """Step 5: Set Task.location_id where area_id is mapped and location_id is NULL."""
    updated = 0
    for legacy_area_id, new_location_id in area_mapping.items():
        count = (
            db.query(Task)
            .filter(
                Task.area_id == legacy_area_id,
                Task.location_id.is_(None),
            )
            .update({"location_id": new_location_id}, synchronize_session="fetch")
        )
        if count:
            logger.info("  Linked %d Task(s) with area_id=%d → location_id=%d",
                        count, legacy_area_id, new_location_id)
            updated += count
    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_migration():
    """Execute the full migration inside a single transaction."""
    logger.info("=" * 60)
    logger.info("Starting Area → Location migration")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        # Step 1 – Areas → Islands
        logger.info("-" * 40)
        logger.info("Step 1/5: Migrating Areas → Island Locations")
        area_mapping = migrate_areas(db)

        # Step 2 – Buildings
        logger.info("-" * 40)
        logger.info("Step 2/5: Migrating Buildings → Building Locations")
        buildings_created = migrate_buildings(db, area_mapping)

        # Step 3 – Streets
        logger.info("-" * 40)
        logger.info("Step 3/5: Migrating Streets → Street Locations")
        streets_created = migrate_streets(db)

        # Step 4 – Backfill Complaints
        logger.info("-" * 40)
        logger.info("Step 4/5: Back-filling Complaint.location_id")
        complaints_updated = backfill_complaints(db, area_mapping)

        # Step 5 – Backfill Tasks
        logger.info("-" * 40)
        logger.info("Step 5/5: Back-filling Task.location_id")
        tasks_updated = backfill_tasks(db, area_mapping)

        db.commit()

        # Summary
        logger.info("=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("  Islands  created : %d", len(area_mapping))
        logger.info("  Buildings created: %d", buildings_created)
        logger.info("  Streets  created : %d", streets_created)
        logger.info("  Complaints linked: %d", complaints_updated)
        logger.info("  Tasks     linked : %d", tasks_updated)
        logger.info("=" * 60)

    except Exception:
        db.rollback()
        logger.exception("Migration failed – all changes rolled back.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
