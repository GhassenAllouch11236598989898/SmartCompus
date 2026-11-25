"""SA-26 — Routes de la mémoire temporaire des conversations (visiteur sans compte)."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession
from app.api.v1.endpoints.sessions import GuestSession
from app.models import Message
from app.models.applications import MessageSender
from app.schemas.memory import ConversationHistory, MessageCreate, MessageOut
from app.services import memory as service

router = APIRouter()


def _to_out(message: Message) -> MessageOut:
    return MessageOut(
        id=message.id,
        sequence=message.sequence,
        sender=message.sender.value,
        content=message.content,
        created_at=message.created_at,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageOut,
    summary="Ajouter un message du visiteur à la mémoire de la conversation",
)
def post_message(payload: MessageCreate, db: DbSession, conversation: GuestSession) -> MessageOut:
    message = service.add_message(db, conversation, MessageSender.user, payload.content)
    return _to_out(message)


@router.get("", response_model=ConversationHistory, summary="Historique récent de la conversation")
def read_history(
    db: DbSession,
    conversation: GuestSession,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
) -> ConversationHistory:
    messages = service.get_recent_messages(db, conversation, limit)
    return ConversationHistory(conversation_id=conversation.id, messages=[_to_out(m) for m in messages])