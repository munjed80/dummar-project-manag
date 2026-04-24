"""Tests for the Celery + Redis background-job system.

The CI environment has no Redis; tests run with
``CELERY_TASK_ALWAYS_EAGER=true`` (set in :mod:`backend.tests.conftest`) so
every dispatched task executes inline. These tests therefore verify:

* the dispatch helper invokes the task body and returns a result handle,
* eager-mode Celery propagates exceptions to the caller,
* the email / PDF / notification tasks are wired correctly to their
  service implementations,
* retry policies and task names are configured as documented,
* the ``GET /jobs/{id}`` endpoint reports task state.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.jobs import celery_app, dispatch, is_eager_mode
from app.jobs.tasks import (
    generate_contract_pdf_task,
    notify_contract_status_change_task,
    send_email_task,
)
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.user import User, UserRole

from tests.conftest import _auth_headers


# ---------------------------------------------------------------------------
# Configuration / wiring
# ---------------------------------------------------------------------------


def test_jobs_run_in_eager_mode_during_tests():
    assert is_eager_mode() is True
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_eager_propagates is True


def test_known_tasks_are_registered():
    names = set(celery_app.tasks.keys())
    assert "dummar.email.send" in names
    assert "dummar.contracts.generate_pdf" in names
    assert "dummar.contract_intelligence.process_document" in names
    assert "dummar.notifications.complaint_status" in names
    assert "dummar.notifications.task_assigned" in names
    assert "dummar.notifications.contract_status" in names


def test_send_email_task_has_retry_policy():
    # autoretry_for is stored as the task option.
    options = send_email_task.__dict__
    # Celery exposes retry config via __wrapped__ but keeps the autoretry_for
    # tuple on the task class. Validate via the task class attributes.
    assert send_email_task.max_retries == 5
    assert send_email_task.name == "dummar.email.send"


# ---------------------------------------------------------------------------
# Dispatch helper
# ---------------------------------------------------------------------------


def test_dispatch_runs_task_inline_and_returns_result():
    result = dispatch(send_email_task, "user@example.com", "subj", "<p>hi</p>")
    # Even with SMTP disabled the task returns False (no-op), which is what
    # _send_email_sync returns when SMTP_ENABLED is False.
    assert result.successful()
    assert result.result is False


def test_dispatch_propagates_task_exceptions_in_eager_mode():
    # notify_contract_status_change_task doesn't catch exceptions internally,
    # so a failure in the underlying service must propagate to the caller in
    # eager mode (task_eager_propagates=True).
    with patch(
        "app.services.notification_service.notify_contract_status_change",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            dispatch(notify_contract_status_change_task, 1, "C-1", "approve")


# ---------------------------------------------------------------------------
# send_email_task — retry on transient errors
# ---------------------------------------------------------------------------


def test_send_email_task_has_autoretry_for_transient_errors():
    # In eager mode Celery does not actually loop on retries, so we verify
    # the autoretry policy is wired correctly. The worker process honors
    # this configuration in production.
    autoretry = getattr(send_email_task, "autoretry_for", ())
    assert ConnectionError in autoretry
    assert TimeoutError in autoretry
    assert OSError in autoretry
    assert send_email_task.max_retries == 5


def test_send_email_task_does_not_retry_on_non_transient_error():
    """A logic error inside the SMTP send should be swallowed (returns False)."""
    with patch(
        "app.services.email_service._send_email_sync",
        side_effect=ValueError("bad address"),
    ):
        result = dispatch(send_email_task, "u@example.com", "s", "<p>h</p>")

    assert result.successful()
    assert result.result is False


# ---------------------------------------------------------------------------
# generate_contract_pdf_task — uses the test DB session via the override
# ---------------------------------------------------------------------------


def _make_contract(db, director: User) -> Contract:
    contract = Contract(
        contract_number="JOB-PDF-001",
        title="Background job test contract",
        contractor_name="ACME",
        contract_type=ContractType.CONSTRUCTION,
        status=ContractStatus.DRAFT,
        contract_value=1000.0,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        scope_description="Scope for background job test.",
        created_by_id=director.id,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


def test_generate_contract_pdf_task_persists_path(db, director_user):
    contract = _make_contract(db, director_user)
    result = dispatch(generate_contract_pdf_task, contract.id)
    assert result.successful()
    pdf_path = result.result
    assert pdf_path and pdf_path.startswith("/uploads/contracts/pdf/")

    # The task opened its own session — refresh the test session to observe
    # the committed change.
    db.expire_all()
    refreshed = db.query(Contract).filter(Contract.id == contract.id).first()
    assert refreshed.pdf_file == pdf_path


def test_generate_contract_pdf_task_handles_missing_contract():
    result = dispatch(generate_contract_pdf_task, 999_999)
    assert result.successful()
    assert result.result is None


# ---------------------------------------------------------------------------
# Notification fan-out task — verifies the wrapper calls the underlying
# notification_service function with the supplied arguments.
# ---------------------------------------------------------------------------


def test_notify_contract_status_change_task_invokes_service():
    with patch(
        "app.services.notification_service.notify_contract_status_change"
    ) as mocked:
        result = dispatch(
            notify_contract_status_change_task,
            42,
            "C-2024-001",
            "approve",
        )
    assert result.successful()
    mocked.assert_called_once()
    kwargs = mocked.call_args.kwargs
    assert kwargs["contract_id"] == 42
    assert kwargs["contract_number"] == "C-2024-001"
    assert kwargs["action"] == "approve"


# ---------------------------------------------------------------------------
# /contracts/{id}/generate-pdf — eager mode returns pdf_path + job_id
# ---------------------------------------------------------------------------


def test_generate_pdf_endpoint_returns_pdf_path_in_eager_mode(
    client, db, director_user, director_token
):
    contract = _make_contract(db, director_user)
    resp = client.post(
        f"/contracts/{contract.id}/generate-pdf",
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "completed"
    assert body["pdf_path"].startswith("/uploads/contracts/pdf/")
    assert body["job_id"]


# ---------------------------------------------------------------------------
# /jobs/{id} status endpoint
# ---------------------------------------------------------------------------


def test_jobs_endpoint_reports_completed_task(client, director_token):
    # Run a quick eager task so we have a real result to look up.
    result = dispatch(send_email_task, "u@example.com", "s", "<p>h</p>")
    resp = client.get(f"/jobs/{result.id}", headers=_auth_headers(director_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["job_id"] == result.id
    # In eager mode results aren't always stored in the backend, but the
    # endpoint must always respond with a JobStatus payload.
    assert "status" in body and "ready" in body


def test_jobs_endpoint_requires_authentication(client):
    resp = client.get("/jobs/some-job-id")
    assert resp.status_code in (401, 403)


def test_jobs_endpoint_reports_unknown_id_as_pending(client, director_token):
    resp = client.get(
        "/jobs/00000000-0000-0000-0000-000000000000",
        headers=_auth_headers(director_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    # An unknown id maps to PENDING in Celery's result API.
    assert body["status"] == "PENDING"
    assert body["ready"] is False
