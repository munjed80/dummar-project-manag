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
