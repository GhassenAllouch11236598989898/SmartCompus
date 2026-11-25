"""SA-25 — Schémas de réponse des sessions visiteurs (sans compte)."""

from datetime import datetime

from pydantic import BaseModel, Field


class GuestSessionCreated(BaseModel):
    """Renvoyé UNE SEULE FOIS à la création : le jeton brut n'est jamais stocké en base."""

    session_token: str = Field(description="Jeton à garder côté navigateur et à renvoyer dans l'en-tête X-Session-Token.")
    conversation_id: int
    expires_at: datetime


class GuestSessionInfo(BaseModel):
    conversation_id: int
    status: str
    started_at: datetime
    last_activity_at: datetime
    expires_at: datetime