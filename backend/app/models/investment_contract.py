"""Investment Contract model.

An InvestmentContract is the legal/financial agreement linked to ONE
InvestmentProperty. The property describes the physical asset; this
contract describes the lease/investment terms and tracks attachments
(contract copy, terms booklet, IDs, ownership proof, handover report,
additional files).

Property data is intentionally NOT duplicated here — only ``property_id``
is stored. The frontend joins ``investment_properties`` for display.
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Enum as SQLEnum,
    ForeignKey, Date, Numeric, Boolean,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enum_utils import enum_values
import enum


class InvestmentType(str, enum.Enum):
    """Type of investment / use granted by the contract."""
    LEASE = "lease"               # إيجار
    INVESTMENT = "investment"     # استثمار
    USUFRUCT = "usufruct"         # حق انتفاع
    PARTNERSHIP = "partnership"   # شراكة
    OTHER = "other"               # غير ذلك


class InvestmentContractStatus(str, enum.Enum):
    """Lifecycle states for an investment contract."""
    ACTIVE = "active"           # فعال
    NEAR_EXPIRY = "near_expiry" # قارب على الانتهاء
    EXPIRED = "expired"         # منتهي
    CANCELLED = "cancelled"     # ملغى


class InvestmentContract(Base):
    __tablename__ = "investment_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_number = Column(String(80), unique=True, nullable=False, index=True)

    # FK to the linked property; required (no contract without a property).
    # Nullable=False enforces "do not create duplicate property records".
    property_id = Column(
        Integer,
        ForeignKey("investment_properties.id"),
        nullable=False,
        index=True,
    )

    investor_name = Column(String(200), nullable=False)
    investor_contact = Column(String(200), nullable=True)

    investment_type = Column(
        SQLEnum(
            InvestmentType,
            name="investmenttype",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=InvestmentType.LEASE,
    )

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    contract_value = Column(Numeric(15, 2), nullable=False)

    status = Column(
        SQLEnum(
            InvestmentContractStatus,
            name="investmentcontractstatus",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=InvestmentContractStatus.ACTIVE,
    )

    notes = Column(Text, nullable=True)

    # Typed attachment slots — each stores a relative upload path or NULL.
    contract_copy = Column(String(255), nullable=True)        # نسخة العقد
    terms_booklet = Column(String(255), nullable=True)        # نسخة دفتر الشروط
    investor_id_copy = Column(String(255), nullable=True)     # صورة هوية المستثمر
    owner_id_copy = Column(String(255), nullable=True)        # صورة هوية المالك
    ownership_proof = Column(String(255), nullable=True)      # إثبات الملكية
    handover_report = Column(String(255), nullable=True)      # محضر التسليم
    handover_property_images = Column(Text, nullable=True)    # صور العقار عند التسليم
    financial_documents = Column(Text, nullable=True)         # مستندات مالية إن وجدت
    # JSON-serialised list of additional attachment paths (مرفقات إضافية)
    additional_attachments = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    property = relationship("InvestmentProperty", foreign_keys=[property_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
