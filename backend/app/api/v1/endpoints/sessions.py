"""SA-25 — Routes des sessions visiteurs (conversation sans création de compte)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import APIKeyHeader

from app.api.deps import DbSession
from app.models import Conversation
from app.schemas.sessions import GuestSessionCreated, GuestSessionInfo
from app.services import sessions as service

router = APIRouter()

_session_header = APIKeyHeader(
    name="X-Session-Token", auto_error=False, description="Jeton de session visiteur (POST /sessions)."
)


def get_guest_session(
    db: DbSession, token: Annotated[str | None, Depends(_session_header)]
) -> Conversation:
    """Dépendance réutilisable (ex. SA-26 /chat) : la session visiteur active de la requête."""
    return service.get_active_guest_session(db, token)


GuestSession = Annotated[Conversation, Depends(get_guest_session)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=GuestSessionCreated,
    summary="Créer une session visiteur (sans compte)",
)
def create_session(db: DbSession) -> GuestSessionCreated:
    token, conversation = service.create_guest_session(db)
    return GuestSessionCreated(
        session_token=token,
        conversation_id=conversation.id,
        expires_at=service.expires_at(conversation),
    )


@router.get("/me", response_model=GuestSessionInfo, summary="Vérifier la session visiteur courante")
def read_session(conversation: GuestSession) -> GuestSessionInfo:
    return GuestSessionInfo(
        conversation_id=conversation.id,
        status=conversation.status.value,
        started_at=conversation.started_at,
        last_activity_at=service.last_activity(conversation),
        expires_at=service.expires_at(conversation),
    )