"""SA-26 — Mémoire temporaire des conversations."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Conversation, Message
from app.models.applications import MessageSender


def _next_sequence(db: Session, conversation: Conversation) -> int:
    current = db.scalar(
        select(func.max(Message.sequence)).where(Message.conversation_id == conversation.id)
    )
    return (current or 0) + 1


def add_message(
    db: Session, conversation: Conversation, sender: MessageSender, content: str
) -> Message:
    """Enregistre un message et met à jour la dernière activité de la conversation."""
    message = Message(
        conversation_id=conversation.id,
        sequence=_next_sequence(db, conversation),
        sender=sender,
        content=content,
    )
    db.add(message)
    conversation.last_message_at = datetime.now(UTC)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(db: Session, conversation: Conversation, limit: int | None = None) -> list[Message]:
    """Les `limit` derniers messages, du plus ancien au plus récent."""
    limit = limit or get_settings().conversation_memory_max_messages
    latest_first = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.sequence.desc())
        .limit(limit)
    ).all()
    return list(reversed(latest_first))


def get_llm_history(db: Session, conversation: Conversation, limit: int | None = None) -> list[dict[str, str]]:
    """Mémoire prête pour le LLM : [{"role": "user"|"assistant"|"system", "content": "..."}]."""
    return [
        {"role": m.sender.value, "content": m.content}
        for m in get_recent_messages(db, conversation, limit)
    ]