from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TeamType(str, enum.Enum):
    INTERNAL_TEAM = "internal_team"
    CONTRACTOR = "contractor"
    FIELD_CREW = "field_crew"
    SUPERVISION_UNIT = "supervision_unit"


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    team_type = Column(SQLEnum(TeamType), nullable=False, default=TeamType.INTERNAL_TEAM)
    contact_name = Column(String(200), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    location = relationship("Location", foreign_keys=[location_id])
    project = relationship("Project", back_populates="teams")
    tasks = relationship("Task", back_populates="team")
