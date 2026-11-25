"""SA-28 — Schémas de l'authentification et de la gestion des rôles."""

from pydantic import BaseModel, Field

from app.models.identity import RoleCode

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegisterRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255, examples=["nour@example.com"])
    password: str = Field(min_length=8, max_length=128, description="8 caractères minimum.")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    roles: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Durée de validité du jeton, en secondes.")
    user: UserOut


class RolesUpdate(BaseModel):
    roles: list[RoleCode] = Field(min_length=1, description="Liste complète des rôles de l'utilisateur.")