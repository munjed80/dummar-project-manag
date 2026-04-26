from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enum_utils import enum_values
import enum


class NotificationType(str, enum.Enum):
    COMPLAINT_STATUS = "complaint_status"
    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    CONTRACT_APPROVED = "contract_approved"
    CONTRACT_UPDATED = "contract_updated"
    INTELLIGENCE_PROCESSING = "intelligence_processing"
    LOCATION_ALERT = "location_alert"
    GENERAL = "general"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(
        SQLEnum(
            NotificationType,
            name="notificationtype",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    entity_type = Column(String(50), nullable=True)  # complaint, task, contract
    entity_id = Column(Integer, nullable=True)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="notifications")
