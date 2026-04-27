"""Guardrails for SQLAlchemy enum persistence vs PostgreSQL enum values."""

from app.models.automation import Automation, AutomationTrigger
from app.models.investment_contract import (
    InvestmentContract,
    InvestmentContractStatus,
    InvestmentType,
)
from app.models.investment_property import InvestmentProperty, PropertyStatus, PropertyType
from app.models.notification import Notification, NotificationType
from app.models.organization import OrgLevel, OrganizationUnit
from app.models.project import Project, ProjectStatus
from app.models.team import Team, TeamType


LOWERCASE_ENUM_COLUMN_EXPECTATIONS = {
    "projectstatus": (Project.__table__.c.status, ProjectStatus),
    "teamtype": (Team.__table__.c.team_type, TeamType),
    "propertytype": (InvestmentProperty.__table__.c.property_type, PropertyType),
    "propertystatus": (InvestmentProperty.__table__.c.status, PropertyStatus),
    "investmenttype": (InvestmentContract.__table__.c.investment_type, InvestmentType),
    "investmentcontractstatus": (InvestmentContract.__table__.c.status, InvestmentContractStatus),
    "automationtrigger": (Automation.__table__.c.trigger, AutomationTrigger),
    "orglevel": (OrganizationUnit.__table__.c.level, OrgLevel),
    "notificationtype": (Notification.__table__.c.notification_type, NotificationType),
}

MIGRATION_ENUM_VALUES = {
    "projectstatus": ["planned", "active", "on_hold", "completed", "cancelled"],
    "teamtype": ["internal_team", "contractor", "field_crew", "supervision_unit"],
    "propertytype": ["building", "land", "restaurant", "kiosk", "shop", "other"],
    "propertystatus": ["available", "invested", "maintenance", "suspended", "unfit"],
    "investmenttype": ["lease", "investment", "usufruct", "partnership", "other"],
    "investmentcontractstatus": ["active", "near_expiry", "expired", "cancelled"],
    "automationtrigger": [
        "complaint_created",
        "complaint_status_changed",
        "task_created",
        "task_status_changed",
    ],
    "orglevel": ["governorate", "municipality", "district"],
    "notificationtype": [
        "complaint_status",
        "task_assigned",
        "task_updated",
        "contract_approved",
        "contract_updated",
        "general",
        "intelligence_processing",
        "location_alert",
    ],
}


def _values(enum_cls) -> list[str]:
    return [member.value for member in enum_cls]


def test_lowercase_pg_enums_persist_enum_values_not_member_names():
    for enum_name, (column, enum_cls) in LOWERCASE_ENUM_COLUMN_EXPECTATIONS.items():
        assert column.type.name == enum_name
        assert column.type.enums == _values(enum_cls)


def test_lowercase_pg_enums_match_alembic_migration_values():
    for enum_name, migration_values in MIGRATION_ENUM_VALUES.items():
        column, enum_cls = LOWERCASE_ENUM_COLUMN_EXPECTATIONS[enum_name]
        assert migration_values == _values(enum_cls)
        assert migration_values == column.type.enums
