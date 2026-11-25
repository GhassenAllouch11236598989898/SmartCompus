"""SA-36 / SA-37 — API du chatbot : session visiteur, dialogue multi-tours avec le LLM, mémoire.

Visiteur sans compte : la session vient de SA-25 (``POST /sessions`` renvoie le jeton, à renvoyer dans
l'en-tête ``X-Session-Token``). Session absente, fermée ou expirée : 401 (dépendance ``GuestSession``).
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession
from app.api.v1.endpoints.sessions import GuestSession
from app.llm.client import LLMClient, get_llm_client
from app.schemas.chat import CandidateMemory, ChatHistory, ChatMessageIn, ChatReply
from app.schemas.common import ERROR_RESPONSES
from app.services import chat as service

router = APIRouter()

LLM = Annotated[LLMClient, Depends(get_llm_client)]


def _responses(*codes: int) -> dict:
    return {c: ERROR_RESPONSES[c] for c in codes}


@router.post(
    "/messages",
    response_model=ChatReply,
    summary="Envoyer un message au chatbot et recevoir sa réponse",
    description="Français, dialecte tunisien (graphie arabe) ou Arabizi. Le LLM reçoit le catalogue officiel, "
    "la mémoire du candidat et les derniers messages de la conversation (dialogue multi-tours).",
    responses=_responses(401, 409, 422, 503),
)
def post_message(payload: ChatMessageIn, db: DbSession, llm: LLM, conversation: GuestSession) -> ChatReply:
    return service.send_message(db, llm, conversation, payload.content)


@router.get(
    "/messages",
    response_model=ChatHistory,
    summary="Historique de la conversation",
    responses=_responses(401),
)
def get_history(db: DbSession, conversation: GuestSession) -> ChatHistory:
    return service.history(db, conversation)


@router.get(
    "/memoire",
    response_model=CandidateMemory,
    summary="Mémoire du chatbot sur le candidat (profil, questions posées)",
    responses=_responses(401),
)
def get_memory(conversation: GuestSession) -> CandidateMemory:
    return service.memory_of(conversation)
