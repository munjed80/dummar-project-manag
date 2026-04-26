from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, text as sa_text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class UserRole(str, enum.Enum):
    PROJECT_DIRECTOR = "project_director"
    CONTRACTS_MANAGER = "contracts_manager"
    ENGINEER_SUPERVISOR = "engineer_supervisor"
    COMPLAINTS_OFFICER = "complaints_officer"
    AREA_SUPERVISOR = "area_supervisor"
    FIELD_TEAM = "field_team"
    CONTRACTOR_USER = "contractor_user"
    CITIZEN = "citizen"
    PROPERTY_MANAGER = "property_manager"
    INVESTMENT_MANAGER = "investment_manager"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CITIZEN)
    phone = Column(String(20), nullable=True)
    is_active = Column(Integer, default=1)
    # Set to True by admin password resets / new accounts that should rotate
    # the temporary password on first login. Cleared by /auth/change-password.
    must_change_password = Column(Boolean, nullable=False, default=False, server_default=sa_text("false"))
    org_unit_id = Column(
        Integer, ForeignKey("organization_units.id"), nullable=True, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    complaints = relationship("Complaint", back_populates="assigned_to_user", foreign_keys="Complaint.assigned_to_id")
    created_tasks = relationship("Task", back_populates="assigned_to_user", foreign_keys="Task.assigned_to_id")
    created_contracts = relationship("Contract", back_populates="created_by_user", foreign_keys="Contract.created_by_id")
    approved_contracts = relationship("Contract", back_populates="approved_by_user", foreign_keys="Contract.approved_by_id")
    audit_logs = relationship("AuditLog", back_populates="user")
    org_unit = relationship("OrganizationUnit", foreign_keys=[org_unit_id])
