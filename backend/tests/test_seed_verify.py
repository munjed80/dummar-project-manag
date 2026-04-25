"""Verify seed_data behavior matches production-readiness requirements."""
import os
import pytest
from app.scripts import seed_data
from app.models.user import User
from app.core.security import verify_password, get_password_hash


def test_fresh_seed_creates_8_users_and_writes_credentials_file(db, tmp_path):
    cred = tmp_path / "seed_credentials.txt"
    seed_data.seed_users(db, credentials_file=str(cred))

    expected = {
        "director", "contracts_mgr", "engineer", "complaints_off",
        "area_sup", "field_user", "contractor", "citizen1",
    }
    usernames = {u.username for u in db.query(User).all()}
    assert expected.issubset(usernames)
    assert cred.exists()
    mode = oct(os.stat(cred).st_mode & 0o777)
    assert mode == "0o600"
    content = cred.read_text()
    creds = {}
    for line in content.splitlines():
        if line.startswith("#") or "\t" not in line:
            continue
        u, p = line.split("\t", 1)
        creds[u] = p
    for u in expected:
        assert u in creds, f"{u} missing from credentials file"
        user = db.query(User).filter(User.username == u).first()
        assert verify_password(creds[u], user.hashed_password)


def test_second_seed_does_not_overwrite_existing_users(db, tmp_path):
    cred = tmp_path / "seed_credentials.txt"
    seed_data.seed_users(db, credentials_file=str(cred))
    hashes_before = {u.username: u.hashed_password for u in db.query(User).all()}

    cred2 = tmp_path / "seed_credentials_2.txt"
    seed_data.seed_users(db, credentials_file=str(cred2))
    hashes_after = {u.username: u.hashed_password for u in db.query(User).all()}

    assert hashes_before == hashes_after
    # No new accounts created → no credentials file written for second run
    assert not cred2.exists()


def test_director_can_login_using_generated_credentials(client, db, tmp_path):
    cred = tmp_path / "seed_credentials.txt"
    seed_data.seed_users(db, credentials_file=str(cred))
    creds = {}
    for line in cred.read_text().splitlines():
        if line.startswith("#") or "\t" not in line:
            continue
        u, p = line.split("\t", 1)
        creds[u] = p
    r = client.post("/auth/login", json={"username": "director", "password": creds["director"]})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_admin_reset_password_sets_must_change_password(client, db, director_token, tmp_path):
    """Director resets a user's password via /users/{id}/reset-password and the
    target's must_change_password becomes True."""
    target = User(
        username="reset_target",
        full_name="t",
        hashed_password=get_password_hash("oldpw"),
        role=__import__("app.models.user", fromlist=["UserRole"]).UserRole.FIELD_TEAM,
        is_active=1,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    headers = {"Authorization": f"Bearer {director_token}"}
    r = client.post(
        f"/users/{target.id}/reset-password",
        json={"new_password": "TempPw!12345"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    db.expire_all()
    refreshed = db.query(User).filter(User.id == target.id).first()
    assert refreshed.must_change_password is True or refreshed.must_change_password == 1
    assert verify_password("TempPw!12345", refreshed.hashed_password)


def test_must_change_password_flag_in_login_response(client, db):
    """A user with must_change_password=True must be flagged in the login token
    response so the frontend can redirect to the change-password page."""
    u = User(
        username="forced_change",
        full_name="x",
        hashed_password=get_password_hash("temp123!"),
        role=__import__("app.models.user", fromlist=["UserRole"]).UserRole.FIELD_TEAM,
        is_active=1,
        must_change_password=True,
    )
    db.add(u)
    db.commit()
    r = client.post("/auth/login", json={"username": "forced_change", "password": "temp123!"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("must_change_password") is True


def test_8_seed_users_login_with_default_password_when_seed_default_passwords_set(
    client, db, tmp_path, monkeypatch
):
    monkeypatch.setenv("SEED_DEFAULT_PASSWORDS", "1")
    seed_data.seed_users(db, credentials_file=str(tmp_path / "x.txt"))
    expected = [
        "director", "contracts_mgr", "engineer", "complaints_off",
        "area_sup", "field_user", "contractor", "citizen1",
    ]
    for u in expected:
        r = client.post("/auth/login", json={"username": u, "password": "password123"})
        assert r.status_code == 200, f"{u} could not log in: {r.text}"
