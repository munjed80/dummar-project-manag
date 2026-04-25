"""Background-job status endpoint.

Allows clients that triggered an async task (e.g. PDF generation, contract
document processing) to poll its progress without needing direct access to
Redis.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_internal_user
from app.jobs import celery_app
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatus(BaseModel):
    job_id: str
    status: str  # PENDING | STARTED | RETRY | FAILURE | SUCCESS | REVOKED
    ready: bool
    successful: Optional[bool] = None
    result: Optional[Any] = None
    error: Optional[str] = None


@router.get("/{job_id}", response_model=JobStatus)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_internal_user),
):
    """Return the current state of a Celery task by id.

    ``status`` follows Celery's standard task states. ``result`` is included
    only on success and is whatever JSON-serialisable value the task
    returned. ``error`` is populated with the traceback summary on failure.
    """
    async_result = celery_app.AsyncResult(job_id)
    state = async_result.state
    payload = JobStatus(
        job_id=job_id,
        status=state,
        ready=async_result.ready(),
    )

    if async_result.ready():
        payload.successful = async_result.successful()
        if async_result.successful():
            try:
                payload.result = async_result.result
            except Exception:
                payload.result = None
        else:
            # async_result.result is the exception instance for FAILURE.
            payload.error = str(async_result.result)

    return payload
