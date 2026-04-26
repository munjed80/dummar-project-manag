from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enum_utils import enum_values
import enum


class ProjectStatus(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(
            ProjectStatus,
            name="projectstatus",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=ProjectStatus.ACTIVE,
    )
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True, index=True)
    org_unit_id = Column(
        Integer, ForeignKey("organization_units.id"), nullable=True, index=True
    )
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    location = relationship("Location", foreign_keys=[location_id])
    contract = relationship("Contract", back_populates="project", foreign_keys="Contract.project_id")
    created_by = relationship("User", foreign_keys=[created_by_id])
    tasks = relationship("Task", back_populates="project")
    complaints = relationship("Complaint", back_populates="project")
    teams = relationship("Team", back_populates="project")
