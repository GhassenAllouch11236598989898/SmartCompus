"""SA-29 — Schémas des conversations rattachées à un compte candidat."""

from datetime import datetime

from pydantic import BaseModel


class CandidateConversation(BaseModel):
    conversation_id: int
    status: str
    started_at: datetime
    last_message_at: datetime | None
    attached_at: datetime | None
    message_count: int