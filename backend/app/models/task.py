from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Date, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskSourceType(str, enum.Enum):
    COMPLAINT = "complaint"
    INTERNAL = "internal"
    CONTRACT = "contract"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    source_type = Column(SQLEnum(TaskSourceType), nullable=False, default=TaskSourceType.INTERNAL)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    org_unit_id = Column(
        Integer, ForeignKey("organization_units.id"), nullable=True, index=True
    )
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True, index=True)
    location_text = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    due_date = Column(Date, nullable=True)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM)
    before_photos = Column(Text, nullable=True)
    after_photos = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    complaint = relationship("Complaint", back_populates="tasks")
    contract = relationship("Contract", back_populates="tasks")
    team = relationship("Team", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    assigned_to_user = relationship("User", back_populates="created_tasks", foreign_keys=[assigned_to_id])
    area = relationship("Area", back_populates="tasks")
    location = relationship("Location", back_populates="tasks", foreign_keys=[location_id])
    activities = relationship("TaskActivity", back_populates="task")


class TaskActivity(Base):
    __tablename__ = "task_activities"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    task = relationship("Task", back_populates="activities")
