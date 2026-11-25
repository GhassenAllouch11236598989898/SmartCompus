"""SA-26 — Schémas des messages de la mémoire conversationnelle."""

from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000, description="Texte du message du visiteur.")


class MessageOut(BaseModel):
    id: int
    sequence: int
    sender: str
    content: str
    created_at: datetime


class ConversationHistory(BaseModel):
    conversation_id: int
    messages: list[MessageOut]