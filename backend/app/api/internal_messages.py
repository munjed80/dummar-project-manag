from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_internal_user
from app.core.database import get_db
from app.models.internal_message import Message, MessageThread, MessageThreadParticipant, MessageThreadType
from app.models.user import User
from app.schemas.internal_message import (
    MessageResponse,
    MessageSendRequest,
    PaginatedThreadListResponse,
    ThreadCreateRequest,
    ThreadDetailResponse,
    ThreadParticipantResponse,
    ThreadSummaryResponse,
)

router = APIRouter(prefix="/internal-messages", tags=["internal-messages"])


def _assert_participant(db: Session, thread_id: int, user_id: int) -> MessageThreadParticipant:
    participant = (
        db.query(MessageThreadParticipant)
        .filter(
            MessageThreadParticipant.thread_id == thread_id,
            MessageThreadParticipant.user_id == user_id,
        )
        .first()
    )
    if participant is None:
        raise HTTPException(status_code=403, detail="Not allowed to access this thread")
    return participant


def _build_thread_summary(db: Session, thread: MessageThread, current_user_id: int) -> ThreadSummaryResponse:
    current_participant = next((p for p in thread.participants if p.user_id == current_user_id), None)
    since = (
        current_participant.last_read_at
        if current_participant and current_participant.last_read_at
        else datetime(1970, 1, 1, tzinfo=timezone.utc)
    )

    unread_count = (
        db.query(func.count(Message.id))
        .filter(
            Message.thread_id == thread.id,
            Message.sender_user_id != current_user_id,
            Message.created_at > since,
        )
        .scalar()
        or 0
    )

    last_message = (
        db.query(Message)
        .filter(Message.thread_id == thread.id)
        .order_by(desc(Message.created_at), desc(Message.id))
        .first()
    )

    return ThreadSummaryResponse(
        id=thread.id,
        title=thread.title,
        thread_type=thread.thread_type,
        created_by_user_id=thread.created_by_user_id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        last_message=MessageResponse.model_validate(last_message) if last_message else None,
        unread_count=unread_count,
        participants=[
            ThreadParticipantResponse(
                user_id=p.user_id,
                joined_at=p.joined_at,
                last_read_at=p.last_read_at,
            )
            for p in thread.participants
        ],
        context_type=thread.context_type,
        context_id=thread.context_id,
        context_title=thread.context_title,
    )


# Set of context_type values that the backend accepts. Phase 2 ships only
# 'complaint' — extend here when wiring contracts/tasks/etc.
SUPPORTED_CONTEXT_TYPES = {"complaint"}


@router.post("/threads", response_model=ThreadSummaryResponse)
def create_thread(
    payload: ThreadCreateRequest,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    participant_ids = set(payload.participant_user_ids)
    participant_ids.add(current_user.id)

    users_count = db.query(User).filter(User.id.in_(participant_ids), User.is_active == 1).count()
    if users_count != len(participant_ids):
        raise HTTPException(status_code=400, detail="One or more participant IDs are invalid")

    thread_type = MessageThreadType.DIRECT if len(participant_ids) == 2 else MessageThreadType.GROUP

    if thread_type == MessageThreadType.DIRECT:
        target_user_id = next(uid for uid in participant_ids if uid != current_user.id)
        candidate_threads = (
            db.query(MessageThread)
            .join(MessageThreadParticipant, MessageThreadParticipant.thread_id == MessageThread.id)
            .filter(
                MessageThread.thread_type == MessageThreadType.DIRECT,
                MessageThreadParticipant.user_id == current_user.id,
            )
            .all()
        )
        for candidate in candidate_threads:
            candidate_user_ids = {p.user_id for p in candidate.participants}
            if candidate_user_ids == {current_user.id, target_user_id}:
                return _build_thread_summary(db, candidate, current_user.id)


    thread = MessageThread(
        title=payload.title.strip() if payload.title else None,
        thread_type=thread_type,
        created_by_user_id=current_user.id,
        context_type=payload.context_type,
        context_id=payload.context_id,
        context_title=payload.context_title,
    )
    db.add(thread)
    db.flush()

    for uid in participant_ids:
        db.add(MessageThreadParticipant(thread_id=thread.id, user_id=uid))

    db.commit()
    db.refresh(thread)
    return _build_thread_summary(db, thread, current_user.id)


@router.get("/threads", response_model=PaginatedThreadListResponse)
def list_threads(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    skip = max(0, skip)

    base_query = (
        db.query(MessageThread)
        .join(MessageThreadParticipant, MessageThreadParticipant.thread_id == MessageThread.id)
        .filter(MessageThreadParticipant.user_id == current_user.id)
    )

    total_count = base_query.count()
    threads = base_query.order_by(desc(MessageThread.updated_at), desc(MessageThread.id)).offset(skip).limit(limit).all()

    return {
        "total_count": total_count,
        "items": [_build_thread_summary(db, thread, current_user.id) for thread in threads],
    }


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(
    thread_id: int,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    participant = _assert_participant(db, thread_id, current_user.id)
    thread = db.query(MessageThread).filter(MessageThread.id == thread_id).first()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at.asc(), Message.id.asc()).all()

    participant.last_read_at = func.now()
    db.commit()
    db.refresh(thread)

    return ThreadDetailResponse(
        thread=_build_thread_summary(db, thread, current_user.id),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
def send_message(
    thread_id: int,
    payload: MessageSendRequest,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    _assert_participant(db, thread_id, current_user.id)

    thread = db.query(MessageThread).filter(MessageThread.id == thread_id).first()
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    msg = Message(thread_id=thread_id, sender_user_id=current_user.id, body=payload.body)
    db.add(msg)
    thread.updated_at = func.now()
    db.commit()
    db.refresh(msg)
    return msg


@router.get(
    "/context/{context_type}/{context_id}",
    response_model=ThreadSummaryResponse,
)
def get_or_create_context_thread(
    context_type: str,
    context_id: int,
    context_title: Optional[str] = None,
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    """Phase-2 contextual thread endpoint.

    If a thread already exists for (context_type, context_id), return it.
    Otherwise create a new GROUP thread linked to that context with the
    current user as the sole participant. The returned shape matches
    ``ThreadSummaryResponse`` so the frontend can immediately reuse the
    standard thread-detail endpoints.

    Currently only ``context_type='complaint'`` is supported.
    """
    if context_type not in SUPPORTED_CONTEXT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported context_type '{context_type}'",
        )
    if context_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid context_id")

    # Validate the referenced entity exists. Currently only complaint is wired.
    if context_type == "complaint":
        from app.models.complaint import Complaint  # local import avoids cycle
        from app.core import permissions as perms

        complaint = db.query(Complaint).filter(Complaint.id == context_id).first()
        if complaint is None:
            raise HTTPException(status_code=404, detail="Complaint not found")
        if perms.is_sensitive_complaint(complaint) and not perms.can_view_sensitive_complaints(current_user):
            raise HTTPException(status_code=404, detail="Complaint not found")

    existing = (
        db.query(MessageThread)
        .filter(
            MessageThread.context_type == context_type,
            MessageThread.context_id == context_id,
        )
        .order_by(MessageThread.id.asc())
        .first()
    )
    if existing is not None:
        # Make sure the current user can participate; auto-add if missing so
        # any internal staff member opening the complaint joins the discussion.
        if not any(p.user_id == current_user.id for p in existing.participants):
            db.add(
                MessageThreadParticipant(
                    thread_id=existing.id,
                    user_id=current_user.id,
                )
            )
            db.commit()
            db.refresh(existing)
        return _build_thread_summary(db, existing, current_user.id)

    thread = MessageThread(
        title=context_title.strip() if context_title else None,
        thread_type=MessageThreadType.GROUP,
        created_by_user_id=current_user.id,
        context_type=context_type,
        context_id=context_id,
        context_title=context_title.strip() if context_title else None,
    )
    db.add(thread)
    db.flush()
    db.add(
        MessageThreadParticipant(thread_id=thread.id, user_id=current_user.id)
    )
    db.commit()
    db.refresh(thread)
    return _build_thread_summary(db, thread, current_user.id)
