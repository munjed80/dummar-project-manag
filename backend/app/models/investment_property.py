from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, ForeignKey, Boolean, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enum_utils import enum_values
import enum


class PropertyType(str, enum.Enum):
    BUILDING = "building"
    LAND = "land"
    RESTAURANT = "restaurant"
    KIOSK = "kiosk"
    SHOP = "shop"
    OTHER = "other"


class PropertyStatus(str, enum.Enum):
    AVAILABLE = "available"
    INVESTED = "invested"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"
    UNFIT = "unfit"


class InvestmentProperty(Base):
    __tablename__ = "investment_properties"

    id = Column(Integer, primary_key=True, index=True)
    property_type = Column(
        SQLEnum(
            PropertyType,
            name="propertytype",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    address = Column(Text, nullable=False)
    area = Column(Numeric(10, 2), nullable=True)
    status = Column(
        SQLEnum(
            PropertyStatus,
            name="propertystatus",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=PropertyStatus.AVAILABLE,
    )
    description = Column(Text, nullable=True)
    owner_name = Column(String(200), nullable=True)
    owner_info = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    created_by = relationship("User", foreign_keys=[created_by_id])
