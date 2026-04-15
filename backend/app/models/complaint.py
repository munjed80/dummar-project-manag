from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base
import enum


class ComplaintType(str, enum.Enum):
    INFRASTRUCTURE = "infrastructure"
    CLEANING = "cleaning"
    ELECTRICITY = "electricity"
    WATER = "water"
    ROADS = "roads"
    LIGHTING = "lighting"
    OTHER = "other"


class ComplaintStatus(str, enum.Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ComplaintPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    complaint_type = Column(SQLEnum(ComplaintType), nullable=False)
    description = Column(Text, nullable=False)
    location_text = Column(Text, nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    geometry = Column(Geometry('POINT', srid=4326), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(SQLEnum(ComplaintStatus), nullable=False, default=ComplaintStatus.NEW)
    priority = Column(SQLEnum(ComplaintPriority), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    images = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    area = relationship("Area", back_populates="complaints")
    assigned_to_user = relationship("User", back_populates="complaints", foreign_keys=[assigned_to_id])
    tasks = relationship("Task", back_populates="complaint")
    activities = relationship("ComplaintActivity", back_populates="complaint")


class ComplaintActivity(Base):
    __tablename__ = "complaint_activities"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    complaint = relationship("Complaint", back_populates="activities")
