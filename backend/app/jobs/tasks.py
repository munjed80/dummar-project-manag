"""Celery task definitions.

All long-running / IO-bound work that used to be performed inline inside
HTTP request handlers lives here. Tasks are intentionally small wrappers
around the existing service functions so the business logic stays
testable in isolation.

Important conventions:

* Tasks accept only JSON-serialisable arguments (typically primary-key
  ints) so they round-trip cleanly through the broker. Any database work
  is performed inside the task using a fresh session obtained from
  :func:`get_task_session_factory`.
* Each task owns its own try/except so a failure inside the task body is
  logged and (optionally) retried via Celery's built-in mechanism instead
  of crashing the worker.
* Logging uses a per-task logger under the ``dummar.jobs`` namespace so
  operators can filter worker logs by task name.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

from celery import Task

from app.core.database import SessionLocal
from app.jobs.celery_app import celery_app

logger = logging.getLogger("dummar.jobs.tasks")


# ---------------------------------------------------------------------------
# Session factory — overridable by tests
# ---------------------------------------------------------------------------

# Tests override this with their in-memory SQLite session factory by calling
# :func:`set_task_session_factory`. Production code never touches it.
_session_factory: Callable[[], Any] = SessionLocal


def set_task_session_factory(factory: Callable[[], Any]) -> None:
    """Override the SQLAlchemy session factory used inside tasks.

    Intended for tests only — production tasks always use the real
    :data:`app.core.database.SessionLocal`.
    """
    global _session_factory
    _session_factory = factory


def get_task_session_factory() -> Callable[[], Any]:
    return _session_factory


@contextmanager
def task_session() -> Iterator[Any]:
    """Yield a fresh DB session and ensure it is closed afterwards."""
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Email — wraps app.services.email_service._send_email_sync
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="dummar.email.send",
    autoretry_for=(ConnectionError, TimeoutError, OSError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)
def send_email_task(self: Task, to_email: str, subject: str, body_html: str) -> bool:
    """Send a single email via the SMTP service.

    Transient network errors trigger Celery's exponential-backoff retry; any
    other exception is logged and the task is marked failed (never retried,
    because retrying e.g. an authentication error wastes worker capacity).
    """
    # Imported lazily so the email module can import dispatch helpers
    # without causing a circular import at package load time.
    from app.services.email_service import _send_email_sync

    try:
        sent = _send_email_sync(to_email, subject, body_html)
        if sent:
            logger.info(
                "send_email_task ok: to=%s subject=%s attempt=%d",
                to_email,
                subject,
                self.request.retries + 1,
            )
        return sent
    except (ConnectionError, TimeoutError, OSError):
        # Re-raise so autoretry_for kicks in.
        logger.warning(
            "send_email_task transient failure (will retry): to=%s subject=%s attempt=%d",
            to_email,
            subject,
            self.request.retries + 1,
        )
        raise
    except Exception:
        logger.exception(
            "send_email_task permanent failure: to=%s subject=%s", to_email, subject
        )
        return False


# ---------------------------------------------------------------------------
# Contract PDF generation
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="dummar.contracts.generate_pdf",
    autoretry_for=(OSError,),
    retry_backoff=True,
    max_retries=3,
)
def generate_contract_pdf_task(self: Task, contract_id: int) -> Optional[str]:
    """Generate the PDF summary for a contract and persist its path.

    Returns the public URL of the generated PDF (e.g.
    ``/uploads/contracts/pdf/contract_X.pdf``), or ``None`` if the contract
    has been deleted between dispatch and execution.
    """
    from app.models.contract import Contract
    from app.services.pdf_generator import generate_contract_pdf

    with task_session() as db:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            logger.warning(
                "generate_contract_pdf_task: contract id=%s not found", contract_id
            )
            return None

        pdf_path = generate_contract_pdf(contract)
        contract.pdf_file = pdf_path
        db.commit()
        logger.info(
            "generate_contract_pdf_task ok: contract id=%s path=%s", contract_id, pdf_path
        )
        return pdf_path


# ---------------------------------------------------------------------------
# Contract intelligence pipeline (OCR + extraction + classification + …)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="dummar.contract_intelligence.process_document",
    autoretry_for=(OSError,),
    retry_backoff=True,
    max_retries=2,
)
def process_contract_document_task(
    self: Task,
    document_id: int,
    filepath: str,
    user_id: int,
) -> bool:
    """Run the full contract-intelligence pipeline on an uploaded document."""
    from app.models.contract_intelligence import ContractDocument
    from app.services.contract_intelligence_pipeline import run_intelligence_pipeline

    with task_session() as db:
        doc = (
            db.query(ContractDocument)
            .filter(ContractDocument.id == document_id)
            .first()
        )
        if not doc:
            logger.warning(
                "process_contract_document_task: document id=%s not found",
                document_id,
            )
            return False

        run_intelligence_pipeline(db, doc, filepath, user_id)
        logger.info(
            "process_contract_document_task ok: document id=%s status=%s",
            document_id,
            doc.processing_status,
        )
        return True


# ---------------------------------------------------------------------------
# Notification fan-out helpers
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="dummar.notifications.complaint_status",
    max_retries=3,
    default_retry_delay=30,
)
def notify_complaint_status_change_task(
    self: Task,
    complaint_id: int,
    tracking_number: str,
    old_status: str,
    new_status: str,
    assigned_to_id: Optional[int] = None,
) -> None:
    from app.services.notification_service import notify_complaint_status_change

    with task_session() as db:
        notify_complaint_status_change(
            db=db,
            complaint_id=complaint_id,
            tracking_number=tracking_number,
            old_status=old_status,
            new_status=new_status,
            assigned_to_id=assigned_to_id,
        )


@celery_app.task(
    bind=True,
    name="dummar.notifications.task_assigned",
    max_retries=3,
    default_retry_delay=30,
)
def notify_task_assigned_task(
    self: Task,
    task_id: int,
    task_title: str,
    assigned_to_id: int,
) -> None:
    from app.services.notification_service import notify_task_assigned

    with task_session() as db:
        notify_task_assigned(
            db=db,
            task_id=task_id,
            task_title=task_title,
            assigned_to_id=assigned_to_id,
        )


@celery_app.task(
    bind=True,
    name="dummar.notifications.contract_status",
    max_retries=3,
    default_retry_delay=30,
)
def notify_contract_status_change_task(
    self: Task,
    contract_id: int,
    contract_number: str,
    action: str,
) -> None:
    from app.services.notification_service import notify_contract_status_change

    with task_session() as db:
        notify_contract_status_change(
            db=db,
            contract_id=contract_id,
            contract_number=contract_number,
            action=action,
        )
