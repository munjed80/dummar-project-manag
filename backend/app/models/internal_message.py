import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Enum as SQLEnum,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.enum_utils import enum_values


class MessageThreadType(str, enum.Enum):
    DIRECT = "direct"
    GROUP = "group"


class MessageThread(Base):
    __tablename__ = "message_threads"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=True)
    thread_type = Column(
        SQLEnum(
            MessageThreadType,
            name="messagethreadtype",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=MessageThreadType.DIRECT,
    )
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    created_by = relationship("User", foreign_keys=[created_by_user_id])
    participants = relationship("MessageThreadParticipant", back_populates="thread", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")


class MessageThreadParticipant(Base):
    __tablename__ = "message_thread_participants"
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_thread_participant"),
    )

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)

    thread = relationship("MessageThread", back_populates="participants")
    user = relationship("User")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("message_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    thread = relationship("MessageThread", back_populates="messages")
    sender = relationship("User")
