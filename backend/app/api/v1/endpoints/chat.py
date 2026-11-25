"""SA-36 / SA-37 — API du chatbot : session visiteur, dialogue multi-tours avec le LLM, mémoire.

Visiteur sans compte : ``POST /chat/sessions`` renvoie un jeton (une seule fois), à renvoyer ensuite dans
l'en-tête ``X-Session-Token``. Seul le SHA-256 du jeton est stocké (``conversations.session_token_hash``).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.api.deps import DbSession
from app.llm.client import LLMClient, get_llm_client
from app.models import Conversation
from app.schemas.chat import CandidateMemory, ChatHistory, ChatMessageIn, ChatReply, ChatSessionCreated
from app.schemas.common import ERROR_RESPONSES
from app.services import chat as service

router = APIRouter()

LLM = Annotated[LLMClient, Depends(get_llm_client)]


def current_conversation(
    db: DbSession,
    x_session_token: Annotated[str, Header(min_length=20, max_length=200, description="Jeton de session visiteur")],
) -> Conversation:
    return service.get_conversation(db, x_session_token)


CurrentConversation = Annotated[Conversation, Depends(current_conversation)]


def _responses(*codes: int) -> dict:
    return {c: ERROR_RESPONSES[c] for c in codes}


@router.post(
    "/sessions",
    response_model=ChatSessionCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Démarrer une conversation (visiteur sans compte)",
)
def create_session(db: DbSession) -> ChatSessionCreated:
    return service.start_session(db)


@router.post(
    "/messages",
    response_model=ChatReply,
    summary="Envoyer un message au chatbot et recevoir sa réponse",
    description="Français, dialecte tunisien (graphie arabe) ou Arabizi. Le LLM reçoit le catalogue officiel, "
    "la mémoire du candidat et les derniers messages de la conversation (dialogue multi-tours).",
    responses=_responses(404, 409, 422, 503),
)
def post_message(payload: ChatMessageIn, db: DbSession, llm: LLM, conversation: CurrentConversation) -> ChatReply:
    return service.send_message(db, llm, conversation, payload.content)


@router.get(
    "/messages",
    response_model=ChatHistory,
    summary="Historique de la conversation",
    responses=_responses(404, 422),
)
def get_history(db: DbSession, conversation: CurrentConversation) -> ChatHistory:
    return service.history(db, conversation)


@router.get(
    "/memoire",
    response_model=CandidateMemory,
    summary="Mémoire du chatbot sur le candidat (profil, questions posées)",
    responses=_responses(404, 422),
)
def get_memory(conversation: CurrentConversation) -> CandidateMemory:
    return service.memory_of(conversation)
