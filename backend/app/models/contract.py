from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Date, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class ContractType(str, enum.Enum):
    CONSTRUCTION = "construction"
    MAINTENANCE = "maintenance"
    SUPPLY = "supply"
    CONSULTING = "consulting"
    OTHER = "other"


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    contractor_name = Column(String(200), nullable=False)
    contractor_contact = Column(String(100), nullable=True)
    contract_type = Column(SQLEnum(ContractType), nullable=False)
    contract_value = Column(Numeric(15, 2), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    execution_duration_days = Column(Integer, nullable=True)
    status = Column(SQLEnum(ContractStatus), nullable=False, default=ContractStatus.DRAFT)
    scope_description = Column(Text, nullable=False)
    related_areas = Column(Text, nullable=True)
    pdf_file = Column(String(255), nullable=True)
    attachments = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    qr_code = Column(String(255), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    project = relationship("Project", back_populates="contract", foreign_keys=[project_id])
    created_by_user = relationship("User", back_populates="created_contracts", foreign_keys=[created_by_id])
    approved_by_user = relationship("User", back_populates="approved_contracts", foreign_keys=[approved_by_id])
    tasks = relationship("Task", back_populates="contract")
    approval_trail = relationship("ContractApproval", back_populates="contract")
    location_links = relationship("ContractLocation", back_populates="contract")


class ContractApproval(Base):
    __tablename__ = "contract_approvals"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    contract = relationship("Contract", back_populates="approval_trail")
