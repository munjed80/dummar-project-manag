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


def _values(enum_cls) -> list[str]:
    return [member.value for member in enum_cls]


def test_project_and_team_enums_persist_lowercase_values():
    assert Project.__table__.c.status.type.enums == _values(ProjectStatus)
    assert Team.__table__.c.team_type.type.enums == _values(TeamType)


def test_investment_enums_persist_lowercase_values():
    assert InvestmentProperty.__table__.c.property_type.type.enums == _values(PropertyType)
    assert InvestmentProperty.__table__.c.status.type.enums == _values(PropertyStatus)
    assert InvestmentContract.__table__.c.investment_type.type.enums == _values(InvestmentType)
    assert InvestmentContract.__table__.c.status.type.enums == _values(InvestmentContractStatus)


def test_automation_org_and_notification_enums_persist_lowercase_values():
    assert Automation.__table__.c.trigger.type.enums == _values(AutomationTrigger)
    assert OrganizationUnit.__table__.c.level.type.enums == _values(OrgLevel)
    assert Notification.__table__.c.notification_type.type.enums == _values(NotificationType)

