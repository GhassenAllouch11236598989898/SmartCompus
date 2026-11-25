"""Schémas Pydantic du chatbot (SA-36 / SA-37). Champs JSON en anglais snake_case, comme le catalogue."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.applications import MessageLanguage, MessageSender


class ChatSessionCreated(BaseModel):
    conversation_id: int
    session_token: str = Field(description="Jeton de session visiteur, renvoyé une seule fois. "
                                           "À envoyer dans l'en-tête X-Session-Token. Seul son SHA-256 est stocké.")


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=10_000, examples=["9adech el licence info ?"])


class ChatMessageOut(BaseModel):
    sequence: int
    sender: MessageSender
    content: str
    detected_language: MessageLanguage
    created_at: datetime


class CandidateMemory(BaseModel):
    profile: dict[str, Any] = Field(description="Profil mémorisé : niveau, section_bac, moyenne, interets, "
                                                "preferences, contraintes, objectif, formations_evoquees")
    asked_questions: list[str]
    language: MessageLanguage | None
    turns: int


class ChatReply(BaseModel):
    conversation_id: int
    user_message: ChatMessageOut
    reply: ChatMessageOut
    memory: CandidateMemory
    model: str
    latency_ms: float


class ChatHistory(BaseModel):
    conversation_id: int
    messages: list[ChatMessageOut]
