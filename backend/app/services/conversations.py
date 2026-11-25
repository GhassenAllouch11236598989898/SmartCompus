"""SA-29 — Associer une conversation invitée (visiteur sans compte) à un compte candidat."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnauthorizedError, UnprocessableError
from app.models import Candidate, Conversation, Message, User
from app.services.sessions import get_active_guest_session


def _get_candidate(db: Session, user: User) -> Candidate:
    candidate = db.scalars(select(Candidate).where(Candidate.user_id == user.id)).one_or_none()
    if candidate is None:
        raise UnprocessableError("Seul un compte candidat peut récupérer une conversation invitée.")
    return candidate


def attach_guest_conversation(db: Session, user: User, session_token: str | None) -> Conversation:
    """Rattache la conversation de la session visiteur au candidat. Idempotent."""
    conversation = get_active_guest_session(db, session_token)
    candidate = _get_candidate(db, user)

    if conversation.candidate_id == candidate.id:
        return conversation  # déjà rattachée à ce candidat
    if conversation.candidate_id is not None:
        raise ConflictError("Cette conversation est déjà rattachée à un autre compte.")

    conversation.candidate_id = candidate.id
    conversation.attached_at = datetime.now(UTC)
    db.commit()
    return conversation


def try_attach_guest_conversation(db: Session, user: User, session_token: str | None) -> int | None:
    """Version « silencieuse » pour register/login : ne bloque jamais la connexion."""
    if not session_token:
        return None
    try:
        return attach_guest_conversation(db, user, session_token).id
    except (UnauthorizedError, UnprocessableError, ConflictError):
        db.rollback()
        return None


def list_candidate_conversations(db: Session, user: User) -> list[tuple[Conversation, int]]:
    """Conversations du candidat (plus récentes d'abord) avec leur nombre de messages."""
    candidate = _get_candidate(db, user)
    message_count = (
        select(func.count(Message.id)).where(Message.conversation_id == Conversation.id).scalar_subquery()
    )
    rows = db.execute(
        select(Conversation, message_count)
        .where(Conversation.candidate_id == candidate.id)
        .order_by(Conversation.started_at.desc())
    ).all()
    return [(conversation, count) for conversation, count in rows]