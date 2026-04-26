"""Fine-grained authorization core.

Pure Python — no FastAPI imports — so this module is unit-testable without HTTP.

Authorization decisions are a function of three dimensions:
  1. Role        (existing UserRole enum)
  2. Org scope   (governorate → municipality → district hierarchy)
  3. Ownership   (created_by_id / assigned_to_id on the resource)

Convention for legacy / unscoped rows: when a resource's ``org_unit_id`` is
NULL it is treated as visible to everyone (the "lenient" rollout default).
This keeps the 348 existing tests green while still enforcing strict scoping
on every newly-created row.
"""
from __future__ import annotations

import enum
from typing import Iterable, Optional, Set, Tuple

from sqlalchemy.orm import Query, Session

from app.models.user import User, UserRole
from app.models.organization import OrganizationUnit


# ---------------------------------------------------------------------------
# Resource and action enums
# ---------------------------------------------------------------------------


class ResourceType(str, enum.Enum):
    COMPLAINT = "complaint"
    TASK = "task"
    CONTRACT = "contract"
    PROJECT = "project"
    USER = "user"
    AUTOMATION = "automation"
    SETTING = "setting"
    REPORT = "report"
    AUDIT_LOG = "audit_log"
    LOCATION = "location"
    ORGANIZATION = "organization"
    NOTIFICATION = "notification"
    INVESTMENT_PROPERTY = "investment_property"


class Action(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ASSIGN = "assign"
    APPROVE = "approve"
    EXPORT = "export"


# ---------------------------------------------------------------------------
# Static role-permission matrix
# ---------------------------------------------------------------------------
# A second element ``"OWN"`` in the tuple marks the permission as
# ownership-restricted: the role only gets that action on resources they own
# (created_by_id or assigned_to_id == user.id).
# ---------------------------------------------------------------------------

_ALL_INTERNAL_READ: Set[Tuple[ResourceType, Action]] = {
    (rt, Action.READ)
    for rt in ResourceType
    if rt not in (ResourceType.AUDIT_LOG,)
}

ROLE_PERMISSIONS: dict[UserRole, Set[Tuple[ResourceType, Action]]] = {
    UserRole.PROJECT_DIRECTOR: {
        (rt, act) for rt in ResourceType for act in Action
    },
    UserRole.CONTRACTS_MANAGER: _ALL_INTERNAL_READ
    | {
        (ResourceType.CONTRACT, Action.CREATE),
        (ResourceType.CONTRACT, Action.UPDATE),
        (ResourceType.CONTRACT, Action.APPROVE),
        (ResourceType.CONTRACT, Action.EXPORT),
        (ResourceType.PROJECT, Action.CREATE),
        (ResourceType.PROJECT, Action.UPDATE),
        (ResourceType.TASK, Action.CREATE),
        (ResourceType.TASK, Action.UPDATE),
        (ResourceType.INVESTMENT_PROPERTY, Action.CREATE),
        (ResourceType.INVESTMENT_PROPERTY, Action.UPDATE),
        (ResourceType.INVESTMENT_PROPERTY, Action.DELETE),
    },
    UserRole.ENGINEER_SUPERVISOR: _ALL_INTERNAL_READ
    | {
        (ResourceType.TASK, Action.CREATE),
        (ResourceType.TASK, Action.UPDATE),
        (ResourceType.TASK, Action.ASSIGN),
        (ResourceType.COMPLAINT, Action.UPDATE),
        (ResourceType.COMPLAINT, Action.ASSIGN),
    },
    UserRole.COMPLAINTS_OFFICER: _ALL_INTERNAL_READ
    | {
        (ResourceType.COMPLAINT, Action.CREATE),
        (ResourceType.COMPLAINT, Action.UPDATE),
        (ResourceType.COMPLAINT, Action.ASSIGN),
        (ResourceType.TASK, Action.CREATE),
        (ResourceType.TASK, Action.UPDATE),
    },
    UserRole.AREA_SUPERVISOR: _ALL_INTERNAL_READ
    | {
        (ResourceType.COMPLAINT, Action.UPDATE),
        (ResourceType.COMPLAINT, Action.ASSIGN),
        (ResourceType.TASK, Action.CREATE),
        (ResourceType.TASK, Action.UPDATE),
        (ResourceType.TASK, Action.ASSIGN),
    },
    UserRole.FIELD_TEAM: {
        (ResourceType.COMPLAINT, Action.READ),
        (ResourceType.TASK, Action.READ),
        (ResourceType.TASK, Action.UPDATE),  # ownership enforced
        (ResourceType.PROJECT, Action.READ),
        (ResourceType.LOCATION, Action.READ),
        (ResourceType.NOTIFICATION, Action.READ),
    },
    UserRole.CONTRACTOR_USER: {
        (ResourceType.CONTRACT, Action.READ),  # ownership enforced
        (ResourceType.TASK, Action.READ),
        (ResourceType.TASK, Action.UPDATE),  # ownership enforced
        (ResourceType.NOTIFICATION, Action.READ),
    },
    UserRole.CITIZEN: {
        (ResourceType.COMPLAINT, Action.CREATE),
        (ResourceType.COMPLAINT, Action.READ),  # ownership enforced (own only)
    },
    # Property manager: full CRUD on investment properties + internal read.
    UserRole.PROPERTY_MANAGER: _ALL_INTERNAL_READ
    | {
        (ResourceType.INVESTMENT_PROPERTY, Action.CREATE),
        (ResourceType.INVESTMENT_PROPERTY, Action.UPDATE),
        (ResourceType.INVESTMENT_PROPERTY, Action.DELETE),
    },
    # Investment manager: view-only on investment properties for now;
    # contract-management privileges will be granted in a later phase.
    UserRole.INVESTMENT_MANAGER: _ALL_INTERNAL_READ,
}


# Role-action combinations that are owner-only even when the role has the
# permission in the matrix above. Lookup key: (role, resource, action).
OWNERSHIP_REQUIRED: Set[Tuple[UserRole, ResourceType, Action]] = {
    (UserRole.FIELD_TEAM, ResourceType.TASK, Action.UPDATE),
    (UserRole.CONTRACTOR_USER, ResourceType.TASK, Action.UPDATE),
    (UserRole.CONTRACTOR_USER, ResourceType.CONTRACT, Action.READ),
    (UserRole.CITIZEN, ResourceType.COMPLAINT, Action.READ),
}


# ---------------------------------------------------------------------------
# Owner adapters: which attribute(s) on the resource constitute ownership.
# ---------------------------------------------------------------------------
_OWNER_ATTRS: dict[ResourceType, Tuple[str, ...]] = {
    ResourceType.COMPLAINT: ("assigned_to_id",),
    ResourceType.TASK: ("assigned_to_id", "created_by_id"),
    ResourceType.CONTRACT: ("created_by_id", "approved_by_id"),
    ResourceType.PROJECT: ("created_by_id",),
    ResourceType.USER: ("id",),
}


def user_owns(user: User, resource: object, resource_type: ResourceType) -> bool:
    if resource is None or user is None:
        return False
    for attr in _OWNER_ATTRS.get(resource_type, ()):
        if getattr(resource, attr, None) == user.id:
            return True
    return False


# ---------------------------------------------------------------------------
# Org-scope predicate
# ---------------------------------------------------------------------------


def _descendant_ids(db: Session, root_id: int) -> Set[int]:
    """BFS over the children backref to collect ``root_id`` and all descendants."""
    result: Set[int] = {root_id}
    frontier: list[int] = [root_id]
    while frontier:
        rows = (
            db.query(OrganizationUnit.id)
            .filter(OrganizationUnit.parent_id.in_(frontier))
            .all()
        )
        next_ids = [r[0] for r in rows if r[0] not in result]
        if not next_ids:
            break
        result.update(next_ids)
        frontier = next_ids
    return result


def user_scope_unit_ids(db: Session, user: User) -> Optional[Set[int]]:
    """Return the set of OrganizationUnit IDs the user can reach.

    ``None`` means "global" (no org filter applied) — the user has cross-org
    visibility either because they have no ``org_unit_id`` set (legacy/global)
    or because their role grants global reach (PROJECT_DIRECTOR).
    """
    if user is None:
        return set()
    if user.role == UserRole.PROJECT_DIRECTOR and user.org_unit_id is None:
        return None
    if user.org_unit_id is None:
        # Non-director users without an org unit fall back to global read scope
        # for backwards compatibility with seed data; mutations are still gated
        # by the role matrix.
        return None
    return _descendant_ids(db, user.org_unit_id)


def user_can_reach_org(
    db: Session, user: User, target_unit_id: Optional[int]
) -> bool:
    if target_unit_id is None:
        return True  # lenient: unscoped row is visible to everyone
    scope = user_scope_unit_ids(db, user)
    if scope is None:
        return True
    return target_unit_id in scope


# ---------------------------------------------------------------------------
# Top-level decision function
# ---------------------------------------------------------------------------


def has_role_permission(
    role: UserRole, resource_type: ResourceType, action: Action
) -> bool:
    return (resource_type, action) in ROLE_PERMISSIONS.get(role, set())


def authorize(
    db: Session,
    user: User,
    action: Action,
    resource_type: ResourceType,
    *,
    resource: object | None = None,
    org_unit_id: Optional[int] = None,
    require_ownership: bool = False,
) -> bool:
    """Return True iff ``user`` is allowed to perform ``action`` on resource.

    The ``resource`` argument (an ORM instance) enables instance-level checks
    (org scope + ownership). If only ``org_unit_id`` is supplied, the org check
    runs against that ID. ``require_ownership`` forces an ownership check even
    if the role's matrix entry would otherwise grant unrestricted access.
    """
    if user is None or not user.is_active:
        return False

    if not has_role_permission(user.role, resource_type, action):
        return False

    target_org = org_unit_id
    if resource is not None and target_org is None:
        target_org = getattr(resource, "org_unit_id", None)

    if not user_can_reach_org(db, user, target_org):
        return False

    needs_ownership = (
        require_ownership
        or (user.role, resource_type, action) in OWNERSHIP_REQUIRED
    )
    if needs_ownership:
        if resource is None:
            # Without an instance we cannot prove ownership; fail closed.
            return False
        if not user_owns(user, resource, resource_type):
            return False

    return True


# ---------------------------------------------------------------------------
# Query-scoping helper
# ---------------------------------------------------------------------------


def scope_query(
    query: Query,
    db: Session,
    user: User,
    model: type,
    *,
    org_attr: str = "org_unit_id",
) -> Query:
    """Filter ``query`` to rows the user is allowed to see.

    Adds ``WHERE org_unit_id IS NULL OR org_unit_id IN (user's subtree)``.
    Returns the unmodified query when the user has global scope.
    """
    scope = user_scope_unit_ids(db, user)
    if scope is None:
        return query
    column = getattr(model, org_attr)
    return query.filter((column.is_(None)) | (column.in_(scope)))


# ---------------------------------------------------------------------------
# Helpers used by /auth/me
# ---------------------------------------------------------------------------


def list_permissions(role: UserRole) -> list[dict[str, str]]:
    perms = sorted(
        ROLE_PERMISSIONS.get(role, set()), key=lambda t: (t[0].value, t[1].value)
    )
    return [{"resource": rt.value, "action": act.value} for rt, act in perms]


def derive_org_chain(
    db: Session, unit_id: Optional[int]
) -> dict[str, Optional[int]]:
    """Walk ``parent_id`` to return ``{governorate_id, municipality_id, district_id}``."""
    out: dict[str, Optional[int]] = {
        "governorate_id": None,
        "municipality_id": None,
        "district_id": None,
    }
    if unit_id is None:
        return out
    seen: Set[int] = set()
    current = db.query(OrganizationUnit).filter(OrganizationUnit.id == unit_id).first()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        if current.level.value == "governorate":
            out["governorate_id"] = current.id
        elif current.level.value == "municipality":
            out["municipality_id"] = current.id
        elif current.level.value == "district":
            out["district_id"] = current.id
        if current.parent_id is None:
            break
        current = (
            db.query(OrganizationUnit)
            .filter(OrganizationUnit.id == current.parent_id)
            .first()
        )
    return out


def all_actions() -> Iterable[Action]:
    return list(Action)
