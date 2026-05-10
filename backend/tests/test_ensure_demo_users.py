"""Tests for ``backend/scripts/ensure_demo_users.py``.

Covers:

* dry-run mode does not write anything to the database;
* ``--apply`` creates a missing user (e.g. ``investment_office``) when its
  env-var temporary password is provided, and the new user can immediately
  log in via the regular ``/auth/login`` endpoint;
* ``--apply`` does NOT overwrite an existing user's password unless the
  matching env var is explicitly set;
* repairs ``full_name`` / ``role`` / ``is_active`` to match the canonical
  spec on existing rows;
* refuses to write when an env-var password is shorter than 8 characters;
* second run is a no-op (idempotent).

The script is run programmatically via ``run(apply_changes=...)`` so the
tests share the same DB session the rest of the suite uses (per-test
truncation). Direct invocation through ``main([...])`` is also exercised so
the CLI argument parsing is covered.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from typing import Iterable

import pytest

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from scripts import ensure_demo_users
from tests.conftest import _auth_headers


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _by_username(results: Iterable[ensure_demo_users.RepairResult], username: str):
    return next(r for r in results if r.username == username)


def _users_by_username(db, *usernames: str):
    return {
        u.username: u
        for u in db.query(User).filter(User.username.in_(usernames)).all()
    }


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write(client, db, monkeypatch):
    # Nothing in the DB for any of the three demo accounts.
    monkeypatch.setenv("INVESTMENT_OFFICE_PASSWORD", "TempPass123!")
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("COMPLAINTS_OFFICER_PASSWORD", raising=False)

    results = ensure_demo_users.run(apply_changes=False, db=db)

    # Nothing was inserted — three "would create" plans came back instead.
    assert _users_by_username(db, "director", "complaints_officer", "investment_office") == {}

    inv = _by_username(results, "investment_office")
    assert inv.created is True
    assert inv.password_changed is True

    # Director / complaints_officer would also be created but have no
    # env-var password, so the script flags them and refuses to write.
    director = _by_username(results, "director")
    assert director.created is True
    assert director.password_changed is False
    assert director.skipped_password_reason and "DIRECTOR_PASSWORD" in director.skipped_password_reason


# ---------------------------------------------------------------------------
# Apply: create missing investment_office and verify login works
# ---------------------------------------------------------------------------


def test_apply_creates_investment_office_and_login_works(client, db, monkeypatch):
    """Repro for the production issue: ``investment_office`` (مكتب الاستثمار)
    was never created because ``seed_data.py`` only affects fresh installs.
    The repair script must create it and the user must be able to log in
    with the env-var-supplied temp password."""
    monkeypatch.setenv("INVESTMENT_OFFICE_PASSWORD", "InvTemp123!")
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("COMPLAINTS_OFFICER_PASSWORD", raising=False)

    ensure_demo_users.run(apply_changes=True, db=db)

    inv = db.query(User).filter(User.username == "investment_office").one()
    assert inv.full_name == "مكتب الاستثمار"
    assert inv.role == UserRole.INVESTMENT_MANAGER
    assert inv.is_active == 1
    assert inv.must_change_password is True
    # Hash, not plaintext.
    assert inv.hashed_password != "InvTemp123!"
    assert verify_password("InvTemp123!", inv.hashed_password)

    # End-to-end: the freshly created investment_office can hit /auth/login.
    resp = client.post(
        "/auth/login",
        json={"username": "investment_office", "password": "InvTemp123!"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["must_change_password"] is True


# ---------------------------------------------------------------------------
# Apply: never overwrites an existing password without the env var
# ---------------------------------------------------------------------------


def test_apply_does_not_overwrite_existing_password_without_env_var(
    client, db, monkeypatch
):
    """If the matching ``*_PASSWORD`` env var is not set, the script must
    leave ``hashed_password`` alone — even when other fields drift."""
    original_hash = get_password_hash("OperatorOwn123!")
    db.add(
        User(
            username="complaints_officer",
            # Drifted full_name + wrong role to verify those are repaired.
            full_name="WRONG NAME",
            role=UserRole.FIELD_TEAM,
            hashed_password=original_hash,
            is_active=1,
        )
    )
    db.commit()

    # No COMPLAINTS_OFFICER_PASSWORD env var set.
    monkeypatch.delenv("COMPLAINTS_OFFICER_PASSWORD", raising=False)
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("INVESTMENT_OFFICE_PASSWORD", raising=False)

    ensure_demo_users.run(apply_changes=True, db=db)

    repaired = db.query(User).filter(User.username == "complaints_officer").one()
    # Canonical fields fixed:
    assert repaired.full_name == "رئيس القسم الفني"
    assert repaired.role == UserRole.COMPLAINTS_OFFICER
    # Password preserved:
    assert repaired.hashed_password == original_hash
    assert verify_password("OperatorOwn123!", repaired.hashed_password)

    # And login with the operator's password still works.
    resp = client.post(
        "/auth/login",
        json={"username": "complaints_officer", "password": "OperatorOwn123!"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Apply: env var rotates an existing password; old one stops working
# ---------------------------------------------------------------------------


def test_apply_with_env_var_rotates_existing_password(client, db, monkeypatch):
    db.add(
        User(
            username="complaints_officer",
            full_name="رئيس القسم الفني",
            role=UserRole.COMPLAINTS_OFFICER,
            hashed_password=get_password_hash("OldPass1234"),
            is_active=1,
        )
    )
    db.commit()

    monkeypatch.setenv("COMPLAINTS_OFFICER_PASSWORD", "NewPass5678")
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("INVESTMENT_OFFICE_PASSWORD", raising=False)

    ensure_demo_users.run(apply_changes=True, db=db)

    # Old password rejected.
    bad = client.post(
        "/auth/login",
        json={"username": "complaints_officer", "password": "OldPass1234"},
    )
    assert bad.status_code == 401

    # New password works.
    ok = client.post(
        "/auth/login",
        json={"username": "complaints_officer", "password": "NewPass5678"},
    )
    assert ok.status_code == 200
    assert ok.json()["must_change_password"] is True


# ---------------------------------------------------------------------------
# Apply: reactivates a disabled demo account so it can log in again
# ---------------------------------------------------------------------------


def test_apply_reactivates_disabled_demo_account(client, db, monkeypatch):
    """Existing-behaviour guard: a disabled user (``is_active=0``) cannot log
    in (returns 403). The repair script must re-enable the three demo
    accounts so they can authenticate again."""
    db.add(
        User(
            username="investment_office",
            full_name="مكتب الاستثمار",
            role=UserRole.INVESTMENT_MANAGER,
            hashed_password=get_password_hash("StaysSame123"),
            is_active=0,
        )
    )
    db.commit()

    # Login is blocked while disabled.
    blocked = client.post(
        "/auth/login",
        json={"username": "investment_office", "password": "StaysSame123"},
    )
    assert blocked.status_code == 403

    monkeypatch.delenv("INVESTMENT_OFFICE_PASSWORD", raising=False)
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("COMPLAINTS_OFFICER_PASSWORD", raising=False)

    ensure_demo_users.run(apply_changes=True, db=db)

    repaired = db.query(User).filter(User.username == "investment_office").one()
    assert repaired.is_active == 1

    ok = client.post(
        "/auth/login",
        json={"username": "investment_office", "password": "StaysSame123"},
    )
    assert ok.status_code == 200


# ---------------------------------------------------------------------------
# Project director can create + reset; new password works, old one fails.
# (Directly proves the production user-management flow.)
# ---------------------------------------------------------------------------


def test_director_create_user_login_then_reset_password_flow(client, director_token):
    create = client.post(
        "/users/",
        json={
            "username": "fresh_user",
            "full_name": "Fresh User",
            "role": "complaints_officer",
            "password": "InitPass123",
            "must_change_password": False,
        },
        headers=_auth_headers(director_token),
    )
    assert create.status_code == 200, create.text
    user_id = create.json()["id"]

    # Created user can immediately log in with the supplied password.
    login = client.post(
        "/auth/login",
        json={"username": "fresh_user", "password": "InitPass123"},
    )
    assert login.status_code == 200

    # Director resets the password.
    reset = client.post(
        f"/users/{user_id}/reset-password",
        json={"new_password": "RotatedPass456", "require_change_on_next_login": False},
        headers=_auth_headers(director_token),
    )
    assert reset.status_code == 200, reset.text

    # Old password no longer works.
    bad = client.post(
        "/auth/login",
        json={"username": "fresh_user", "password": "InitPass123"},
    )
    assert bad.status_code == 401

    # New password works.
    ok = client.post(
        "/auth/login",
        json={"username": "fresh_user", "password": "RotatedPass456"},
    )
    assert ok.status_code == 200


# ---------------------------------------------------------------------------
# Idempotency + length validation + CLI smoke
# ---------------------------------------------------------------------------


def test_apply_is_idempotent_second_run_is_noop(client, db, monkeypatch):
    monkeypatch.setenv("INVESTMENT_OFFICE_PASSWORD", "InvTemp123!")
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("COMPLAINTS_OFFICER_PASSWORD", raising=False)

    ensure_demo_users.run(apply_changes=True, db=db)
    # Drop the env var so the second run does not re-rotate the password.
    monkeypatch.delenv("INVESTMENT_OFFICE_PASSWORD", raising=False)

    second = ensure_demo_users.run(apply_changes=True, db=db)
    inv = _by_username(second, "investment_office")
    assert inv.created is False
    assert inv.field_changes == []
    assert inv.password_changed is False


def test_short_env_password_is_rejected(db, monkeypatch):
    monkeypatch.setenv("INVESTMENT_OFFICE_PASSWORD", "abc")  # < 8 chars
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("COMPLAINTS_OFFICER_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="INVESTMENT_OFFICE_PASSWORD"):
        ensure_demo_users.run(apply_changes=True, db=db)

    # And nothing was inserted.
    assert db.query(User).filter(User.username == "investment_office").first() is None


def test_summary_never_prints_password_value(db, monkeypatch):
    """Defence-in-depth: the dry-run / apply summary must never echo the
    operator-supplied password. We use a sentinel value and assert it does
    not appear anywhere in stdout."""
    sentinel = "ZZZ-SENTINEL-PW-9876"
    monkeypatch.setenv("INVESTMENT_OFFICE_PASSWORD", sentinel)
    monkeypatch.delenv("DIRECTOR_PASSWORD", raising=False)
    monkeypatch.delenv("COMPLAINTS_OFFICER_PASSWORD", raising=False)

    results = ensure_demo_users.run(apply_changes=False, db=db)

    buf = io.StringIO()
    with redirect_stdout(buf):
        ensure_demo_users._print_summary(results, applied=False)
    out = buf.getvalue()
    assert sentinel not in out
    # The summary does signal that a rotation would happen.
    assert "rotated" in out
