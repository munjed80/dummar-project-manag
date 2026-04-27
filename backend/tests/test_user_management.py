"""Tests for the user/auth admin flows.

Covers:
  * login for every UserRole (project_director, contracts_manager,
    engineer_supervisor, complaints_officer, area_supervisor, field_team,
    contractor_user, citizen)
  * inactive user is blocked from logging in (and receives 403 if they
    somehow present a stale token)
  * admin can create a user without supplying an email
  * admin can update role / mark user inactive
  * admin can reset another user's password (and the reset forces a
    must_change_password rotation)
  * first-login self-service password change flow:
      - GET /auth/me reflects the must_change_password flag
      - POST /auth/change-password rejects wrong current password
      - POST /auth/change-password rejects "same as old"
      - POST /auth/change-password succeeds, clears the flag, and the
        user can log in with the new password
  * seed_users() is idempotent and never overwrites a manually created
    operator account.
  * pdf_generator module imports/parses cleanly (regression guard for
    the historical f-string-with-backslash SyntaxError).
"""

import importlib

import pytest

from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from tests.conftest import _auth_headers, _login


ALL_ROLES = [
    UserRole.PROJECT_DIRECTOR,
    UserRole.CONTRACTS_MANAGER,
    UserRole.ENGINEER_SUPERVISOR,
    UserRole.COMPLAINTS_OFFICER,
    UserRole.AREA_SUPERVISOR,
    UserRole.FIELD_TEAM,
    UserRole.CONTRACTOR_USER,
    UserRole.CITIZEN,
]


# ---------------------------------------------------------------------------
# Login matrix — every role must be able to authenticate.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("role", ALL_ROLES, ids=lambda r: r.value)
def test_login_succeeds_for_every_role(client, db, role):
    user = User(
        username=f"user_{role.value}",
        full_name=f"User {role.value}",
        hashed_password=get_password_hash("Sup3rSecret!"),
        role=role,
        is_active=1,
    )
    db.add(user)
    db.commit()

    resp = client.post(
        "/auth/login",
        json={"username": user.username, "password": "Sup3rSecret!"},
    )
    assert resp.status_code == 200, f"Login failed for role {role.value}: {resp.text}"
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    # Newly created accounts default to must_change_password=False here
    # because we built the User row directly (not via the API).
    assert body["must_change_password"] is False


def test_login_with_wrong_password_returns_401(client, db):
    db.add(User(
        username="locked", full_name="Locked",
        hashed_password=get_password_hash("rightpass"),
        role=UserRole.FIELD_TEAM, is_active=1,
    ))
    db.commit()
    resp = client.post(
        "/auth/login", json={"username": "locked", "password": "wrong"}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Inactive user is blocked.
# ---------------------------------------------------------------------------

def test_inactive_user_cannot_log_in(client, db):
    db.add(User(
        username="suspended", full_name="Suspended",
        hashed_password=get_password_hash("password123"),
        role=UserRole.FIELD_TEAM, is_active=0,
    ))
    db.commit()

    resp = client.post(
        "/auth/login",
        json={"username": "suspended", "password": "password123"},
    )
    assert resp.status_code == 403
    assert "inactive" in resp.json()["detail"].lower()


def test_inactive_user_with_stale_token_blocked(client, db, field_user, field_token):
    # Deactivate the user *after* the token was issued.
    field_user.is_active = 0
    db.commit()

    resp = client.get("/auth/me", headers=_auth_headers(field_token))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin user-management flow.
# ---------------------------------------------------------------------------

def test_admin_can_create_user(client, director_token):
    payload = {
        "username": "operator1",
        "full_name": "Operator One",
        "role": "engineer_supervisor",
        "phone": "+963900000001",
        "password": "Sup3rSecret!",
    }
    resp = client.post("/users/", json=payload, headers=_auth_headers(director_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == "operator1"
    # No email field is exposed — the system has no email concept.
    assert "email" not in body
    # API-created accounts default to requiring a password rotation.
    assert body["must_change_password"] is True


def test_admin_create_user_rejects_email_field(client, director_token):
    """Email is not part of the user model — extra ``email`` keys must not
    silently flow into the database."""
    resp = client.post(
        "/users/",
        json={
            "username": "noemail",
            "full_name": "No Email",
            "role": "field_team",
            "password": "Sup3rSecret!",
            "email": "should-be-ignored@example.com",
        },
        headers=_auth_headers(director_token),
    )
    # Pydantic v2 ignores extra fields by default; the create still succeeds
    # but the response/payload must not contain the email.
    assert resp.status_code == 200, resp.text
    assert "email" not in resp.json()


def test_admin_create_user_short_password_rejected(client, director_token):
    resp = client.post(
        "/users/",
        json={
            "username": "tiny",
            "full_name": "Tiny",
            "role": "field_team",
            "password": "short",
        },
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 422


def test_admin_can_change_role_and_phone_and_full_name(client, director_token, db):
    db.add(User(
        username="op2", full_name="Op Two",
        hashed_password=get_password_hash("password123"),
        role=UserRole.FIELD_TEAM, is_active=1,
    ))
    db.commit()
    user = db.query(User).filter(User.username == "op2").first()

    resp = client.put(
        f"/users/{user.id}",
        json={
            "full_name": "Op Two Renamed",
            "role": "engineer_supervisor",
            "phone": "+963900000002",
        },
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["full_name"] == "Op Two Renamed"
    assert body["role"] == "engineer_supervisor"
    assert body["phone"] == "+963900000002"


def test_director_can_update_another_users_username(client, director_token, db):
    db.add(User(
        username="rename_me", full_name="Rename Me",
        hashed_password=get_password_hash("password123"),
        role=UserRole.FIELD_TEAM, is_active=1,
    ))
    db.commit()
    user = db.query(User).filter(User.username == "rename_me").first()

    resp = client.put(
        f"/users/{user.id}",
        json={"username": "renamed_user"},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["username"] == "renamed_user"


def test_duplicate_or_blank_username_update_is_rejected(client, director_token, db):
    db.add_all([
        User(
            username="existing_name", full_name="Existing Name",
            hashed_password=get_password_hash("password123"),
            role=UserRole.FIELD_TEAM, is_active=1,
        ),
        User(
            username="target_name", full_name="Target Name",
            hashed_password=get_password_hash("password123"),
            role=UserRole.FIELD_TEAM, is_active=1,
        ),
    ])
    db.commit()
    target = db.query(User).filter(User.username == "target_name").first()

    duplicate = client.put(
        f"/users/{target.id}",
        json={"username": "existing_name"},
        headers=_auth_headers(director_token),
    )
    assert duplicate.status_code == 400
    assert "exists" in duplicate.json()["detail"].lower()

    blank = client.put(
        f"/users/{target.id}",
        json={"username": "   "},
        headers=_auth_headers(director_token),
    )
    assert blank.status_code == 422
    assert "username" in str(blank.json()).lower()


def test_director_full_user_management_flow(client, director_token):
    # 1) create user
    create = client.post(
        "/users/",
        json={
            "username": "manage_me",
            "full_name": "Manage Me",
            "role": "field_team",
            "phone": "+963911111111",
            "password": "InitPass123!",
            "must_change_password": False,
        },
        headers=_auth_headers(director_token),
    )
    assert create.status_code == 200, create.text
    user_id = create.json()["id"]

    # 2) edit username + full name + role + must_change_password
    update = client.put(
        f"/users/{user_id}",
        json={
            "username": "managed_user",
            "full_name": "Managed User Updated",
            "role": "area_supervisor",
            "must_change_password": True,
        },
        headers=_auth_headers(director_token),
    )
    assert update.status_code == 200, update.text
    body = update.json()
    assert body["username"] == "managed_user"
    assert body["full_name"] == "Managed User Updated"
    assert body["role"] == "area_supervisor"
    assert body["must_change_password"] is True

    # 3) reset password
    reset = client.post(
        f"/users/{user_id}/reset-password",
        json={"new_password": "ResetPass456!", "require_change_on_next_login": False},
        headers=_auth_headers(director_token),
    )
    assert reset.status_code == 200, reset.text

    # 4) deactivate
    deactivate = client.delete(f"/users/{user_id}", headers=_auth_headers(director_token))
    assert deactivate.status_code == 200

    denied_login = client.post(
        "/auth/login",
        json={"username": "managed_user", "password": "ResetPass456!"},
    )
    assert denied_login.status_code == 403

    # 5) reactivate
    reactivate = client.put(
        f"/users/{user_id}",
        json={"is_active": 1},
        headers=_auth_headers(director_token),
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] == 1

    # 6) modified user can login with the reset password
    login = client.post(
        "/auth/login",
        json={"username": "managed_user", "password": "ResetPass456!"},
    )
    assert login.status_code == 200, login.text


def test_non_admin_cannot_manage_users(client, field_token):
    create = client.post(
        "/users/",
        json={
            "username": "forbidden_create",
            "full_name": "Forbidden Create",
            "role": "field_team",
            "password": "SomePass123!",
        },
        headers=_auth_headers(field_token),
    )
    assert create.status_code == 403

    list_resp = client.get("/users/", headers=_auth_headers(field_token))
    assert list_resp.status_code == 403


def test_admin_can_deactivate_user_via_update(client, director_token, db):
    db.add(User(
        username="op3", full_name="Op Three",
        hashed_password=get_password_hash("password123"),
        role=UserRole.FIELD_TEAM, is_active=1,
    ))
    db.commit()
    user = db.query(User).filter(User.username == "op3").first()

    resp = client.put(
        f"/users/{user.id}",
        json={"is_active": 0},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] == 0


def test_director_cannot_demote_or_deactivate_self(client, director_token, director_user):
    resp = client.put(
        f"/users/{director_user.id}",
        json={"role": "field_team"},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 400

    resp = client.put(
        f"/users/{director_user.id}",
        json={"is_active": 0},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 400

    resp = client.delete(
        f"/users/{director_user.id}",
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Admin password reset.
# ---------------------------------------------------------------------------

def test_admin_can_reset_password_and_user_must_change_on_next_login(
    client, director_token, db
):
    db.add(User(
        username="forgetful", full_name="Forgetful",
        hashed_password=get_password_hash("OldPass123"),
        role=UserRole.AREA_SUPERVISOR, is_active=1,
    ))
    db.commit()
    user = db.query(User).filter(User.username == "forgetful").first()

    resp = client.post(
        f"/users/{user.id}/reset-password",
        json={"new_password": "BrandNew456"},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["must_change_password"] is True

    # Old password no longer works.
    bad = client.post(
        "/auth/login",
        json={"username": "forgetful", "password": "OldPass123"},
    )
    assert bad.status_code == 401

    # New password works and the login response surfaces the rotation flag.
    ok = client.post(
        "/auth/login",
        json={"username": "forgetful", "password": "BrandNew456"},
    )
    assert ok.status_code == 200
    assert ok.json()["must_change_password"] is True


def test_admin_password_reset_short_password_rejected(client, director_token, db):
    db.add(User(
        username="weakreset", full_name="Weak",
        hashed_password=get_password_hash("OldPass123"),
        role=UserRole.AREA_SUPERVISOR, is_active=1,
    ))
    db.commit()
    user = db.query(User).filter(User.username == "weakreset").first()
    resp = client.post(
        f"/users/{user.id}/reset-password",
        json={"new_password": "tiny"},
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 422


def test_admin_password_reset_can_skip_rotation_flag(client, director_token, db):
    db.add(User(
        username="trusted", full_name="Trusted",
        hashed_password=get_password_hash("OldPass123"),
        role=UserRole.AREA_SUPERVISOR, is_active=1,
    ))
    db.commit()
    user = db.query(User).filter(User.username == "trusted").first()
    resp = client.post(
        f"/users/{user.id}/reset-password",
        json={
            "new_password": "BrandNew456",
            "require_change_on_next_login": False,
        },
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is False


def test_non_director_cannot_reset_password(client, field_token, db):
    db.add(User(
        username="victim", full_name="Victim",
        hashed_password=get_password_hash("OldPass123"),
        role=UserRole.AREA_SUPERVISOR, is_active=1,
    ))
    db.commit()
    user = db.query(User).filter(User.username == "victim").first()

    resp = client.post(
        f"/users/{user.id}/reset-password",
        json={"new_password": "Hacked123!"},
        headers=_auth_headers(field_token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# First-login self-service password change.
# ---------------------------------------------------------------------------

def test_first_login_change_password_flow(client, director_token, db):
    # Director provisions an account that must rotate on first login.
    create = client.post(
        "/users/",
        json={
            "username": "firstlogin",
            "full_name": "First Login",
            "role": "field_team",
            "password": "Initial123",
        },
        headers=_auth_headers(director_token),
    )
    assert create.status_code == 200
    assert create.json()["must_change_password"] is True

    # Login surfaces the flag.
    login = client.post(
        "/auth/login",
        json={"username": "firstlogin", "password": "Initial123"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["must_change_password"] is True
    token = body["access_token"]

    # /auth/me also surfaces it (so frontend route guards can redirect).
    me = client.get("/auth/me", headers=_auth_headers(token))
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    # Wrong current_password rejected.
    bad = client.post(
        "/auth/change-password",
        json={"current_password": "WrongPass", "new_password": "Rotated123"},
        headers=_auth_headers(token),
    )
    assert bad.status_code == 400

    # Same password rejected.
    same = client.post(
        "/auth/change-password",
        json={"current_password": "Initial123", "new_password": "Initial123"},
        headers=_auth_headers(token),
    )
    assert same.status_code == 400

    # Successful rotation.
    ok = client.post(
        "/auth/change-password",
        json={"current_password": "Initial123", "new_password": "Rotated123"},
        headers=_auth_headers(token),
    )
    assert ok.status_code == 200
    assert ok.json()["must_change_password"] is False

    # Old password no longer works; new one does and flag is cleared.
    assert client.post(
        "/auth/login",
        json={"username": "firstlogin", "password": "Initial123"},
    ).status_code == 401

    relogin = client.post(
        "/auth/login",
        json={"username": "firstlogin", "password": "Rotated123"},
    )
    assert relogin.status_code == 200
    assert relogin.json()["must_change_password"] is False


def test_change_password_short_new_password_rejected(client, field_token):
    resp = client.post(
        "/auth/change-password",
        json={"current_password": "testpass123", "new_password": "tiny"},
        headers=_auth_headers(field_token),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Seed idempotency.
# ---------------------------------------------------------------------------

def test_seed_users_does_not_overwrite_manually_created_user(db, monkeypatch, tmp_path):
    """seed_users() must skip any username that already exists in the DB,
    preserving the operator-created hashed_password / role / phone."""
    from app.scripts import seed_data

    # Manually create one of the seed usernames with a custom password / role.
    custom_hash = get_password_hash("MyOwnPass!")
    db.add(User(
        username="director",
        full_name="Manually Created Director",
        hashed_password=custom_hash,
        role=UserRole.PROJECT_DIRECTOR,
        phone="+963999999999",
        is_active=1,
    ))
    db.commit()

    # Force the legacy default-password mode so the test is deterministic.
    monkeypatch.setenv("SEED_DEFAULT_PASSWORDS", "1")

    creds_file = tmp_path / "creds.txt"
    seed_data.seed_users(db, credentials_file=str(creds_file))

    preserved = db.query(User).filter(User.username == "director").one()
    # Hash and full_name must be unchanged.
    assert preserved.hashed_password == custom_hash
    assert preserved.full_name == "Manually Created Director"
    assert preserved.phone == "+963999999999"
    assert verify_password("MyOwnPass!", preserved.hashed_password)

    # Other seed users were created (idempotent ADD, not overwrite).
    assert db.query(User).filter(User.username == "engineer").first() is not None


def test_seed_users_runs_twice_without_error(db, monkeypatch, tmp_path):
    from app.scripts import seed_data

    monkeypatch.setenv("SEED_DEFAULT_PASSWORDS", "1")

    seed_data.seed_users(db, credentials_file=str(tmp_path / "c1.txt"))
    count_after_first = db.query(User).count()
    seed_data.seed_users(db, credentials_file=str(tmp_path / "c2.txt"))
    count_after_second = db.query(User).count()
    assert count_after_first == count_after_second


# ---------------------------------------------------------------------------
# Regression guard for the historic pdf_generator SyntaxError.
# ---------------------------------------------------------------------------

def test_pdf_generator_module_imports_cleanly():
    """The pdf_generator module previously contained an f-string with a
    backslash that broke import on Python <3.12. Importing here is a smoke
    test that no such syntax is reintroduced."""
    mod = importlib.import_module("app.services.pdf_generator")
    assert hasattr(mod, "generate_contract_pdf")
