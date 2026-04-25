"""Organization unit model — administrative hierarchy for fine-grained RBAC.

Hierarchy: GOVERNORATE → MUNICIPALITY → DISTRICT.
A unit's parent (if any) must be exactly one level shallower.
"""
import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OrgLevel(str, enum.Enum):
    GOVERNORATE = "governorate"
    MUNICIPALITY = "municipality"
    DISTRICT = "district"


# Ordered shallow→deep for one-step-deeper validation.
_ORDER = [OrgLevel.GOVERNORATE, OrgLevel.MUNICIPALITY, OrgLevel.DISTRICT]


def expected_child_level(parent_level: "OrgLevel | None") -> "OrgLevel | None":
    """Return the only valid child level for a given parent level (or None for root)."""
    if parent_level is None:
        return OrgLevel.GOVERNORATE
    idx = _ORDER.index(parent_level)
    if idx + 1 >= len(_ORDER):
        return None  # district has no valid children
    return _ORDER[idx + 1]


class OrganizationUnit(Base):
    __tablename__ = "organization_units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    level = Column(SQLEnum(OrgLevel, name="orglevel"), nullable=False, index=True)
    parent_id = Column(
        Integer, ForeignKey("organization_units.id"), nullable=True, index=True
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    parent = relationship("OrganizationUnit", remote_side=[id], backref="children")
