"""ensure_demo_users.py — safe, non-destructive repair of the three required
demo / role accounts (director, complaints_officer, investment_office).

Why this exists
---------------
``app/scripts/seed_data.py`` only inserts users that do not already exist, so
it has *no effect* on a database that has already been seeded once. As a
result, accounts added to the seed list later (notably ``investment_office``
for مكتب الاستثمار) never appear in production, and any drift in the
``full_name`` / ``role`` / ``is_active`` of the three operator-facing demo
accounts cannot be corrected by re-running the seeder.

This script targets only the three accounts listed in ``DEMO_USERS`` below
and:

* creates them if they are missing,
* updates ``full_name`` / ``role`` / ``is_active`` on existing rows so they
  match the canonical spec (the ones operators expect to see in the UI),
* optionally rotates each account's password — but **only** when the
  matching environment variable is explicitly provided, so a routine run
  never silently overwrites a password an operator has already set.

It is **dry-run by default**. Pass ``--apply`` to actually write changes.

Passwords are hashed with the same ``app.core.security.get_password_hash``
helper used by the production login flow (passlib bcrypt) and are **never**
printed, logged, or written to disk.

Usage::

    # Show what would change, write nothing:
    python backend/scripts/ensure_demo_users.py --dry-run

    # Actually create / update the three accounts (no password changes):
    python backend/scripts/ensure_demo_users.py --apply

    # Actually create / update *and* rotate two passwords:
    COMPLAINTS_OFFICER_PASSWORD='...' INVESTMENT_OFFICE_PASSWORD='...' \\
        python backend/scripts/ensure_demo_users.py --apply

The script is intentionally limited to the three accounts in ``DEMO_USERS``
so an operator running it can never accidentally mass-edit other users.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional

# Make the ``app`` package importable when this script is run directly from
# a checkout (``python backend/scripts/ensure_demo_users.py``) — same trick
# ``app/scripts/seed_data.py`` already uses.
_BACKEND_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


# ---------------------------------------------------------------------------
# Canonical spec for the three demo / role accounts.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    full_name: str
    role: UserRole
    password_env_var: str


DEMO_USERS: List[DemoUserSpec] = [
    DemoUserSpec(
        username="director",
        full_name="د. ضياء",
        role=UserRole.PROJECT_DIRECTOR,
        password_env_var="DIRECTOR_PASSWORD",
    ),
    DemoUserSpec(
        username="complaints_officer",
        full_name="رئيس القسم الفني",
        role=UserRole.COMPLAINTS_OFFICER,
        password_env_var="COMPLAINTS_OFFICER_PASSWORD",
    ),
    DemoUserSpec(
        username="investment_office",
        full_name="مكتب الاستثمار",
        role=UserRole.INVESTMENT_MANAGER,
        password_env_var="INVESTMENT_OFFICE_PASSWORD",
    ),
]

# Matches the ``min_length=8`` Pydantic constraint on
# ``schemas.user.AdminPasswordReset.new_password`` so a too-short env var is
# rejected here instead of silently producing an unusable account.
_MIN_PASSWORD_LENGTH = 8


# ---------------------------------------------------------------------------
# Per-account repair plan / execution.
# ---------------------------------------------------------------------------

@dataclass
class RepairResult:
    username: str
    created: bool = False
    field_changes: List[str] = None  # type: ignore[assignment]
    password_changed: bool = False
    skipped_password_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.field_changes is None:
            self.field_changes = []

    @property
    def is_noop(self) -> bool:
        return not (self.created or self.field_changes or self.password_changed)


def _read_password(spec: DemoUserSpec) -> Optional[str]:
    """Return the env-var-supplied temporary password, or None if unset.

    Empty / whitespace-only values are treated as unset so an operator
    cannot accidentally clear a password by exporting an empty variable.
    """
    raw = os.environ.get(spec.password_env_var, "")
    if not raw or not raw.strip():
        return None
    return raw


def _plan_for_user(db: Session, spec: DemoUserSpec, password: Optional[str]) -> RepairResult:
    """Compute (without writing) what would change for one demo account."""
    result = RepairResult(username=spec.username)

    user = db.query(User).filter(User.username == spec.username).first()

    if user is None:
        result.created = True
        if password is None:
            # Cannot create an account without a password — flag it.
            result.skipped_password_reason = (
                f"missing — set {spec.password_env_var} to create this account"
            )
        else:
            result.password_changed = True
        return result

    # Existing row — only canonical-spec fields are repaired.
    if user.full_name != spec.full_name:
        result.field_changes.append(
            f"full_name: {user.full_name!r} -> {spec.full_name!r}"
        )
    if user.role != spec.role:
        old = user.role.value if user.role is not None else None
        result.field_changes.append(f"role: {old} -> {spec.role.value}")
    # ``is_active`` is an Integer column (1/0); spec requires active=True.
    if not user.is_active:
        result.field_changes.append(f"is_active: {user.is_active} -> 1")

    if password is not None:
        result.password_changed = True
    else:
        # Existing row, no env password — leave hashed_password alone.
        result.skipped_password_reason = (
            f"unchanged ({spec.password_env_var} not set)"
        )

    return result


def _apply_for_user(
    db: Session, spec: DemoUserSpec, password: Optional[str], plan: RepairResult
) -> None:
    """Mutate the DB to match the planned changes (caller commits)."""
    user = db.query(User).filter(User.username == spec.username).first()

    if user is None:
        # ``_plan_for_user`` already recorded ``skipped_password_reason`` if
        # the env var was missing; without a password we cannot create.
        if password is None:
            return
        user = User(
            username=spec.username,
            full_name=spec.full_name,
            role=spec.role,
            hashed_password=get_password_hash(password),
            # User.is_active is an Integer column (1/0) — see column-types
            # convention; pass the integer explicitly.
            is_active=1,
            # New accounts must rotate the temp password on first login. The
            # operator-supplied env-var password is treated as a temporary
            # bootstrap credential.
            must_change_password=True,
        )
        db.add(user)
        return

    # Update canonical fields.
    if user.full_name != spec.full_name:
        user.full_name = spec.full_name
    if user.role != spec.role:
        user.role = spec.role
    if not user.is_active:
        user.is_active = 1

    if password is not None:
        user.hashed_password = get_password_hash(password)
        # Force the user to rotate the operator-supplied temp password,
        # matching the behaviour of the admin reset-password endpoint.
        user.must_change_password = True


# ---------------------------------------------------------------------------
# Reporting.
# ---------------------------------------------------------------------------

def _print_summary(results: Iterable[RepairResult], *, applied: bool) -> None:
    header = (
        "Applied changes:" if applied else "Dry run — the following changes would be made:"
    )
    print(header)
    print("-" * len(header))

    any_change = False
    for r in results:
        prefix = "+" if r.created else "~"
        if r.is_noop:
            print(f"  . {r.username}: no changes needed")
            if r.skipped_password_reason:
                print(f"      password: {r.skipped_password_reason}")
            continue

        any_change = True
        action = "CREATE" if r.created else "UPDATE"
        print(f"  {prefix} {r.username}: {action}")
        for change in r.field_changes:
            print(f"      {change}")
        if r.password_changed:
            print("      password: rotated (value not shown)")
        elif r.skipped_password_reason:
            print(f"      password: {r.skipped_password_reason}")

    if not any_change:
        print("\nAll three demo accounts are already in the desired state.")
    elif not applied:
        print("\nRe-run with --apply to write these changes.")


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------

def run(apply_changes: bool, db: Optional[Session] = None) -> List[RepairResult]:
    """Programmatic entry point. Returns the per-user repair results.

    The optional ``db`` argument is intended for tests so they can pass a
    transactional session that is rolled back / truncated by the fixture.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        passwords = {spec.username: _read_password(spec) for spec in DEMO_USERS}
        # Validate password length up-front so a too-short env var aborts
        # before any rows are written.
        for spec in DEMO_USERS:
            pw = passwords[spec.username]
            if pw is not None and len(pw) < _MIN_PASSWORD_LENGTH:
                raise ValueError(
                    f"{spec.password_env_var} must be at least "
                    f"{_MIN_PASSWORD_LENGTH} characters; refusing to write."
                )

        plans = [_plan_for_user(db, spec, passwords[spec.username]) for spec in DEMO_USERS]

        if apply_changes:
            for spec, plan in zip(DEMO_USERS, plans):
                _apply_for_user(db, spec, passwords[spec.username], plan)
            db.commit()

        return plans
    finally:
        if own_session:
            db.close()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Safe, non-destructive repair of the three required demo / role "
            "accounts (director, complaints_officer, investment_office). "
            "Dry-run by default."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the changes that would be made without writing (default).",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Actually write the changes to the database.",
    )
    args = parser.parse_args(argv)

    apply_changes = bool(args.apply)

    try:
        results = run(apply_changes=apply_changes)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    _print_summary(results, applied=apply_changes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
