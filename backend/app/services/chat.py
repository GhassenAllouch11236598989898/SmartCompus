"""SA-36 / SA-37 — Dialogue multi-tours avec le LLM.

Un tour de conversation :

1. retrouver la conversation par le hash du jeton de session (visiteur anonyme) ;
2. détecter la langue du message (``app.llm.language``) ;
3. mettre à jour la mémoire longue (profil candidat, questions posées) ;
4. construire le prompt : règles + catalogue + mémoire + fenêtre des derniers messages + message ;
5. appeler le LLM ; en cas d'échec, rien n'est enregistré (le candidat peut renvoyer son message) ;
6. enregistrer le message du candidat et la réponse (``messages``), la mémoire (``conversations.memory``).

Le contenu des messages n'est jamais journalisé.
"""

import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, ServiceUnavailableError, UnprocessableError
from app.core.security import hash_token
from app.llm.client import ChatMessage, LLMClient, LLMError
from app.llm.language import detect_language, language_label
from app.llm.memory import ConversationMemory, HistoryItem, build_history, profile_from_llm
from app.llm.prompts import CHAT_SYSTEM, PROFILE_EXTRACT_SYSTEM
from app.llm.text import parse_json_object
from app.models import Conversation, Message
from app.models.applications import ConversationStatus, MessageLanguage, MessageSender
from app.schemas.chat import CandidateMemory, ChatHistory, ChatMessageOut, ChatReply, ChatSessionCreated
from app.services.chat_context import catalogue_context

logger = logging.getLogger("smartcampus.chat")

ContextProvider = Callable[[Session], str]


# ------------------------------------------------------------------ sessions
def start_session(db: Session) -> ChatSessionCreated:
    """Ouvre une conversation visiteur. Point de raccord avec les sessions visiteurs (SA-23 à SA-25)."""
    token = secrets.token_urlsafe(32)
    conversation = Conversation(session_token_hash=hash_token(token))
    db.add(conversation)
    db.commit()
    return ChatSessionCreated(conversation_id=conversation.id, session_token=token)


def get_conversation(db: Session, session_token: str) -> Conversation:
    conversation = db.scalars(
        select(Conversation).where(Conversation.session_token_hash == hash_token(session_token))
    ).first()
    if conversation is None:
        raise NotFoundError("Session de conversation inconnue ou expirée.")
    return conversation


# ------------------------------------------------------------------ lecture
def _out(m: Message) -> ChatMessageOut:
    return ChatMessageOut(sequence=m.sequence, sender=m.sender, content=m.content,
                          detected_language=m.detected_language, created_at=m.created_at)


def history(db: Session, conversation: Conversation) -> ChatHistory:
    messages = db.scalars(
        select(Message).where(Message.conversation_id == conversation.id, Message.sender != MessageSender.system)
        .order_by(Message.sequence)
    ).all()
    return ChatHistory(conversation_id=conversation.id, messages=[_out(m) for m in messages])


def memory_of(conversation: Conversation) -> CandidateMemory:
    mem = ConversationMemory.from_json(conversation.memory)
    language = mem.language if mem.language in MessageLanguage._value2member_map_ else None
    return CandidateMemory(profile=mem.profile, asked_questions=mem.questions, language=language, turns=mem.turns)


# ------------------------------------------------------------------ dialogue
def _recent_items(db: Session, conversation: Conversation, limit: int) -> list[HistoryItem]:
    rows = db.scalars(
        select(Message).where(Message.conversation_id == conversation.id, Message.sender != MessageSender.system)
        .order_by(Message.sequence.desc()).limit(limit)
    ).all()
    return [HistoryItem(m.sender.value, m.content) for m in reversed(rows)]


def build_prompt(
    catalogue: str, memory: ConversationMemory, past: list[HistoryItem], message: str, language: MessageLanguage
) -> list[ChatMessage]:
    settings = get_settings()
    system = CHAT_SYSTEM.format(language=language_label(language), catalogue=catalogue, memory=memory.to_prompt())
    window = build_history(past, max_messages=settings.llm_memory_max_messages,
                           max_chars=settings.llm_memory_max_chars)
    return [ChatMessage("system", system), *window, ChatMessage("user", message)]


def _llm_profile(llm: LLMClient, message: str) -> dict:
    """Extraction du profil par le LLM (option LLM_MEMORY_EXTRACTION=llm). Échec -> règles seules."""
    try:
        raw = llm.chat([ChatMessage("system", PROFILE_EXTRACT_SYSTEM), ChatMessage("user", message)],
                       temperature=0.0, max_tokens=200, json_mode=True).content
    except LLMError:
        return {}
    return profile_from_llm(parse_json_object(raw))


def send_message(
    db: Session,
    llm: LLMClient,
    conversation: Conversation,
    content: str,
    *,
    context_provider: ContextProvider = catalogue_context,
) -> ChatReply:
    settings = get_settings()
    content = content.strip()
    if not content:
        raise UnprocessableError("Le message est vide.")
    if len(content) > settings.chat_message_max_chars:
        raise UnprocessableError(f"Message trop long (maximum {settings.chat_message_max_chars} caractères).")
    if conversation.status != ConversationStatus.active:
        raise ConflictError("Cette conversation est clôturée.")

    guess = detect_language(content)
    memory = ConversationMemory.from_json(conversation.memory)
    past = _recent_items(db, conversation, settings.llm_memory_max_messages)
    extracted = _llm_profile(llm, content) if settings.llm_memory_extraction == "llm" else None
    memory.observe_user_message(content, guess.language.value, extracted)

    prompt = build_prompt(context_provider(db), memory, past, content, guess.language)
    try:
        answer = llm.chat(prompt)
    except LLMError:
        db.rollback()
        logger.warning("Conversation %s : LLM indisponible", conversation.id)
        raise ServiceUnavailableError("L'assistant est momentanément indisponible. Réessayez dans un instant.") from None
    reply_text = answer.content.strip() or "Désolé, je n'ai pas compris. Pouvez-vous reformuler ?"
    reply_lang = detect_language(reply_text)

    last = db.scalar(select(func.max(Message.sequence)).where(Message.conversation_id == conversation.id)) or 0
    user_msg = Message(conversation_id=conversation.id, sequence=last + 1, sender=MessageSender.user,
                       content=content, detected_language=guess.language, language_confidence=guess.confidence)
    bot_msg = Message(conversation_id=conversation.id, sequence=last + 2, sender=MessageSender.assistant,
                      content=reply_text, detected_language=reply_lang.language,
                      language_confidence=reply_lang.confidence)
    db.add_all([user_msg, bot_msg])
    conversation.last_message_at = datetime.now(UTC)
    conversation.memory = memory.to_json()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Un autre message est en cours de traitement pour cette conversation. Réessayez.") from None
    logger.info("Conversation %s : tour %d (%s, %.0f ms)", conversation.id, memory.turns, guess.language.value,
                answer.latency_ms)
    return ChatReply(conversation_id=conversation.id, user_message=_out(user_msg), reply=_out(bot_msg),
                     memory=memory_of(conversation), model=answer.model, latency_ms=answer.latency_ms)
