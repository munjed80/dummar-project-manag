from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base
import enum


# ---------------------------------------------------------------------------
# Location type hierarchy enum
# ---------------------------------------------------------------------------

class LocationType(str, enum.Enum):
    ISLAND = "island"
    SECTOR = "sector"
    BLOCK = "block"
    BUILDING = "building"
    TOWER = "tower"
    STREET = "street"
    SERVICE_POINT = "service_point"
    OTHER = "other"


class LocationStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_CONSTRUCTION = "under_construction"
    DEMOLISHED = "demolished"


# ---------------------------------------------------------------------------
# Unified Location model with parent-child hierarchy
# ---------------------------------------------------------------------------

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    location_type = Column(SQLEnum(LocationType), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)
    status = Column(SQLEnum(LocationStatus), nullable=False, default=LocationStatus.ACTIVE)
    description = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    boundary_path = Column(Text, nullable=True)  # JSON polygon for area boundaries
    metadata_json = Column(Text, nullable=True)  # Flexible metadata as JSON
    is_active = Column(Integer, default=1, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Self-referential parent-child
    parent = relationship("Location", remote_side=[id], back_populates="children")
    children = relationship("Location", back_populates="parent", order_by="Location.name")

    # Reverse relationships to operational entities
    complaints = relationship("Complaint", back_populates="location", foreign_keys="Complaint.location_id")
    tasks = relationship("Task", back_populates="location", foreign_keys="Task.location_id")
    contract_links = relationship("ContractLocation", back_populates="location")


# ---------------------------------------------------------------------------
# Many-to-many: Contract <-> Location coverage
# ---------------------------------------------------------------------------

class ContractLocation(Base):
    __tablename__ = "contract_locations"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    contract = relationship("Contract", back_populates="location_links")
    location = relationship("Location", back_populates="contract_links")


# ---------------------------------------------------------------------------
# Legacy tables (kept for backward compatibility with existing data)
# ---------------------------------------------------------------------------

class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    name_ar = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    geometry = Column(Geometry('POLYGON', srid=4326), nullable=True)
    boundary_polygon = Column(Text, nullable=True)  # JSON array of [lat, lng] pairs
    color = Column(String(20), nullable=True)  # hex color for map display
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    buildings = relationship("Building", back_populates="area")
    complaints = relationship("Complaint", back_populates="area")
    tasks = relationship("Task", back_populates="area")


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    building_number = Column(String(20), nullable=True)
    floors = Column(Integer, nullable=True)
    geometry = Column(Geometry('POINT', srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    area = relationship("Area", back_populates="buildings")


class Street(Base):
    __tablename__ = "streets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    code = Column(String(20), nullable=True)
    geometry = Column(Geometry('LINESTRING', srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
