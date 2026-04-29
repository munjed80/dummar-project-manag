from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_internal_user
from app.core.database import get_db
from app.models.internal_message import MessageThread, MessageThreadParticipant, Message, MessageThreadType
from app.models.user import User
from app.schemas.internal_message import (
    ThreadCreateRequest,
    ThreadSummaryResponse,
    ThreadDetailResponse,
    ThreadParticipantResponse,
    MessageResponse,
    MessageSendRequest,
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
    thread = MessageThread(
        title=payload.title,
        thread_type=thread_type,
        created_by_user_id=current_user.id,
    )
    db.add(thread)
    db.flush()

    for uid in participant_ids:
        db.add(MessageThreadParticipant(thread_id=thread.id, user_id=uid))

    db.commit()
    db.refresh(thread)

    participants = [
        ThreadParticipantResponse(user_id=p.user_id, joined_at=p.joined_at, last_read_at=p.last_read_at)
        for p in thread.participants
    ]
    return ThreadSummaryResponse(
        id=thread.id,
        title=thread.title,
        thread_type=thread.thread_type,
        created_by_user_id=thread.created_by_user_id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        last_message=None,
        unread_count=0,
        participants=participants,
    )


@router.get("/threads", response_model=list[ThreadSummaryResponse])
def list_threads(
    current_user: User = Depends(get_current_internal_user),
    db: Session = Depends(get_db),
):
    threads = (
        db.query(MessageThread)
        .join(MessageThreadParticipant, MessageThreadParticipant.thread_id == MessageThread.id)
        .filter(MessageThreadParticipant.user_id == current_user.id)
        .order_by(desc(MessageThread.updated_at))
        .all()
    )

    output = []
    for thread in threads:
        current_participant = next((p for p in thread.participants if p.user_id == current_user.id), None)
        unread_count = (
            db.query(func.count(Message.id))
            .filter(
                Message.thread_id == thread.id,
                Message.sender_user_id != current_user.id,
                Message.created_at > (current_participant.last_read_at if current_participant and current_participant.last_read_at else datetime(1970, 1, 1, tzinfo=timezone.utc)),
            )
            .scalar()
        )
        last_message = (
            db.query(Message)
            .filter(Message.thread_id == thread.id)
            .order_by(desc(Message.created_at))
            .first()
        )
        output.append(
            ThreadSummaryResponse(
                id=thread.id,
                title=thread.title,
                thread_type=thread.thread_type,
                created_by_user_id=thread.created_by_user_id,
                created_at=thread.created_at,
                updated_at=thread.updated_at,
                last_message=MessageResponse.model_validate(last_message) if last_message else None,
                unread_count=unread_count or 0,
                participants=[
                    ThreadParticipantResponse(
                        user_id=p.user_id,
                        joined_at=p.joined_at,
                        last_read_at=p.last_read_at,
                    )
                    for p in thread.participants
                ],
            )
        )
    return output


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

    messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at.asc()).all()

    participant.last_read_at = func.now()
    db.commit()
    db.refresh(participant)

    summary = ThreadSummaryResponse(
        id=thread.id,
        title=thread.title,
        thread_type=thread.thread_type,
        created_by_user_id=thread.created_by_user_id,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        last_message=MessageResponse.model_validate(messages[-1]) if messages else None,
        unread_count=0,
        participants=[
            ThreadParticipantResponse(user_id=p.user_id, joined_at=p.joined_at, last_read_at=p.last_read_at)
            for p in thread.participants
        ],
    )

    return ThreadDetailResponse(
        thread=summary,
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
