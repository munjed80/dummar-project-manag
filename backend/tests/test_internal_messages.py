from tests.conftest import _auth_headers, _create_user, _login
from app.models.user import UserRole


def test_create_direct_thread_and_prevent_duplicates(client, db):
    _create_user(db, "msg_director", UserRole.PROJECT_DIRECTOR)
    other = _create_user(db, "msg_engineer", UserRole.ENGINEER_SUPERVISOR)

    token = _login(client, "msg_director")
    payload = {"participant_user_ids": [other.id]}

    first = client.post("/internal-messages/threads", json=payload, headers=_auth_headers(token))
    assert first.status_code == 200, first.text
    first_id = first.json()["id"]

    second = client.post("/internal-messages/threads", json=payload, headers=_auth_headers(token))
    assert second.status_code == 200, second.text
    assert second.json()["id"] == first_id


def test_send_and_read_messages_flow(client, db):
    _create_user(db, "msg_manager", UserRole.PROJECT_DIRECTOR)
    receiver = _create_user(db, "msg_field", UserRole.FIELD_TEAM)

    manager_token = _login(client, "msg_manager")
    field_token = _login(client, "msg_field")

    create = client.post(
        "/internal-messages/threads",
        json={"participant_user_ids": [receiver.id]},
        headers=_auth_headers(manager_token),
    )
    assert create.status_code == 200, create.text
    thread_id = create.json()["id"]

    send = client.post(
        f"/internal-messages/threads/{thread_id}/messages",
        json={"body": "مرحبا من الإدارة"},
        headers=_auth_headers(manager_token),
    )
    assert send.status_code == 200, send.text

    list_before = client.get("/internal-messages/threads", headers=_auth_headers(field_token))
    assert list_before.status_code == 200
    assert list_before.json()["total_count"] == 1
    assert list_before.json()["items"][0]["unread_count"] == 1

    detail = client.get(f"/internal-messages/threads/{thread_id}", headers=_auth_headers(field_token))
    assert detail.status_code == 200
    assert len(detail.json()["messages"]) == 1

    list_after = client.get("/internal-messages/threads", headers=_auth_headers(field_token))
    assert list_after.status_code == 200
    assert list_after.json()["items"][0]["unread_count"] == 0


def test_reject_blank_messages(client, db):
    _create_user(db, "msg_contracts", UserRole.CONTRACTS_MANAGER)
    other = _create_user(db, "msg_officer", UserRole.COMPLAINTS_OFFICER)
    token = _login(client, "msg_contracts")

    create = client.post(
        "/internal-messages/threads",
        json={"participant_user_ids": [other.id]},
        headers=_auth_headers(token),
    )
    assert create.status_code == 200
    thread_id = create.json()["id"]

    send = client.post(
        f"/internal-messages/threads/{thread_id}/messages",
        json={"body": "   "},
        headers=_auth_headers(token),
    )
    assert send.status_code == 422


# ── Phase 2: context-linked threads ──────────────────────────────────────────


def _make_complaint(db, tracking="CTX001"):
    from app.models.complaint import Complaint, ComplaintType, ComplaintStatus

    c = Complaint(
        tracking_number=tracking,
        full_name="Ctx Citizen",
        phone="0991111111",
        complaint_type=ComplaintType.OTHER,
        description="ctx test",
        status=ComplaintStatus.NEW,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_context_thread_creates_when_missing(client, db):
    _create_user(db, "ctx_director", UserRole.PROJECT_DIRECTOR)
    token = _login(client, "ctx_director")
    complaint = _make_complaint(db, tracking="CTX_NEW1")

    resp = client.get(
        f"/internal-messages/context/complaint/{complaint.id}?context_title=Ticket%20A",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["context_type"] == "complaint"
    assert data["context_id"] == complaint.id
    assert data["context_title"] == "Ticket A"
    assert data["thread_type"] == "group"
    assert any(p["user_id"] for p in data["participants"])


def test_context_thread_is_idempotent(client, db):
    _create_user(db, "ctx_dup", UserRole.PROJECT_DIRECTOR)
    token = _login(client, "ctx_dup")
    complaint = _make_complaint(db, tracking="CTX_DUP1")

    first = client.get(
        f"/internal-messages/context/complaint/{complaint.id}",
        headers=_auth_headers(token),
    )
    second = client.get(
        f"/internal-messages/context/complaint/{complaint.id}",
        headers=_auth_headers(token),
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_context_thread_auto_adds_new_participant(client, db):
    _create_user(db, "ctx_owner", UserRole.PROJECT_DIRECTOR)
    other = _create_user(db, "ctx_other", UserRole.ENGINEER_SUPERVISOR)
    owner_token = _login(client, "ctx_owner")
    other_token = _login(client, "ctx_other")
    complaint = _make_complaint(db, tracking="CTX_JOIN1")

    first = client.get(
        f"/internal-messages/context/complaint/{complaint.id}",
        headers=_auth_headers(owner_token),
    )
    assert first.status_code == 200
    thread_id = first.json()["id"]

    joined = client.get(
        f"/internal-messages/context/complaint/{complaint.id}",
        headers=_auth_headers(other_token),
    )
    assert joined.status_code == 200
    assert joined.json()["id"] == thread_id
    user_ids = {p["user_id"] for p in joined.json()["participants"]}
    assert other.id in user_ids


def test_context_thread_rejects_unknown_context_type(client, db):
    _create_user(db, "ctx_bad", UserRole.PROJECT_DIRECTOR)
    token = _login(client, "ctx_bad")
    resp = client.get(
        "/internal-messages/context/contract/1",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 400


def test_context_thread_404_when_complaint_missing(client, db):
    _create_user(db, "ctx_404", UserRole.PROJECT_DIRECTOR)
    token = _login(client, "ctx_404")
    resp = client.get(
        "/internal-messages/context/complaint/999999",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 404
