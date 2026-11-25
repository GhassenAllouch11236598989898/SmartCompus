"""SA-28 — Routes d'authentification et de gestion des rôles.
SA-29 — Rattachement de la conversation invitée au compte candidat.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import DbSession, get_current_user, require_roles
from app.api.v1.endpoints.sessions import _session_header
from app.models import User
from app.models.identity import RoleCode
from app.schemas.auth import LoginRequest, RegisterRequest, RolesUpdate, TokenResponse, UserOut
from app.schemas.conversations import CandidateConversation
from app.services import auth as service
from app.services import conversations as conversation_service

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_user)]
Admin = Annotated[User, Depends(require_roles(RoleCode.admin))]
# SA-29 : jeton de session visiteur, facultatif (envoyé par le frontend s'il existe).
SessionToken = Annotated[str | None, Depends(_session_header)]


def _to_conversation(conversation, message_count: int) -> CandidateConversation:
    return CandidateConversation(
        conversation_id=conversation.id,
        status=conversation.status.value,
        started_at=conversation.started_at,
        last_message_at=conversation.last_message_at,
        attached_at=conversation.attached_at,
        message_count=message_count,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    summary="Créer un compte candidat (récupère la conversation invitée si X-Session-Token est fourni)",
)
def register(payload: RegisterRequest, db: DbSession, session_token: SessionToken) -> TokenResponse:
    user = service.register_candidate(db, payload)
    attached_id = conversation_service.try_attach_guest_conversation(db, user, session_token)
    return service.issue_token(user).model_copy(update={"attached_conversation_id": attached_id})


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Se connecter (récupère la conversation invitée si X-Session-Token est fourni)",
)
def login(payload: LoginRequest, db: DbSession, session_token: SessionToken) -> TokenResponse:
    user = service.authenticate(db, payload.email, payload.password)
    attached_id = conversation_service.try_attach_guest_conversation(db, user, session_token)
    return service.issue_token(user).model_copy(update={"attached_conversation_id": attached_id})


@router.get("/me", response_model=UserOut, summary="Mon compte et mes rôles")
def me(user: CurrentUser) -> UserOut:
    return service.user_out(user)


@router.post(
    "/me/conversations/attach",
    response_model=CandidateConversation,
    summary="Rattacher ma conversation invitée à mon compte candidat (JWT + X-Session-Token)",
)
def attach_conversation(db: DbSession, user: CurrentUser, session_token: SessionToken) -> CandidateConversation:
    conversation = conversation_service.attach_guest_conversation(db, user, session_token)
    return _to_conversation(conversation, len(conversation.messages))


@router.get(
    "/me/conversations",
    response_model=list[CandidateConversation],
    summary="Mes conversations (dont celles commencées avant la création du compte)",
)
def my_conversations(db: DbSession, user: CurrentUser) -> list[CandidateConversation]:
    return [_to_conversation(c, n) for c, n in conversation_service.list_candidate_conversations(db, user)]


@router.put(
    "/users/{user_id}/roles",
    response_model=UserOut,
    summary="Modifier les rôles d'un utilisateur (admin uniquement)",
)
def update_roles(
    payload: RolesUpdate,
    db: DbSession,
    admin: Admin,
    user_id: Annotated[int, Path(ge=1)],
) -> UserOut:
    user = service.set_user_roles(db, admin, user_id, payload.roles)
    return service.user_out(user)