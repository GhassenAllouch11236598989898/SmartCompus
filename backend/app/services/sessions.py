"""SA-25 — Gestion des sessions des visiteurs (sans compte)."""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.security import hash_token
from app.models import Conversation
from app.models.applications import ConversationStatus

INVALID_SESSION_MESSAGE = "Session visiteur invalide ou expirée. Créez une nouvelle session."


def _ttl() -> timedelta:
    return timedelta(hours=get_settings().guest_session_ttl_hours)


def last_activity(conversation: Conversation) -> datetime:
    return conversation.last_message_at or conversation.started_at


def expires_at(conversation: Conversation) -> datetime:
    return last_activity(conversation) + _ttl()


def create_guest_session(db: Session) -> tuple[str, Conversation]:
    """Crée une session visiteur. Retourne (jeton brut, conversation)."""
    token = secrets.token_urlsafe(32)
    conversation = Conversation(
        session_token_hash=hash_token(token),
        started_at=datetime.now(UTC),
    )
    db.add(conversation)
    db.commit()
    return token, conversation


def get_active_guest_session(db: Session, token: str | None) -> Conversation:
    """Retrouve la session à partir du jeton. Erreur 401 si absente, fermée ou expirée."""
    if not token:
        raise UnauthorizedError("En-tête X-Session-Token manquant.")

    conversation = db.scalars(
        select(Conversation).where(Conversation.session_token_hash == hash_token(token))
    ).one_or_none()

    if conversation is None or conversation.status != ConversationStatus.active:
        raise UnauthorizedError(INVALID_SESSION_MESSAGE)

    if expires_at(conversation) <= datetime.now(UTC):
        conversation.status = ConversationStatus.closed
        db.commit()
        raise UnauthorizedError(INVALID_SESSION_MESSAGE)

    return conversation