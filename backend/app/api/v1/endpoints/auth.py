"""SA-28 — Routes d'authentification et de gestion des rôles."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import DbSession, get_current_user, require_roles
from app.models import User
from app.models.identity import RoleCode
from app.schemas.auth import LoginRequest, RegisterRequest, RolesUpdate, TokenResponse, UserOut
from app.services import auth as service

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_user)]
Admin = Annotated[User, Depends(require_roles(RoleCode.admin))]


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
    summary="Créer un compte candidat",
)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    user = service.register_candidate(db, payload)
    return service.issue_token(user)


@router.post("/login", response_model=TokenResponse, summary="Se connecter (email + mot de passe)")
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = service.authenticate(db, payload.email, payload.password)
    return service.issue_token(user)


@router.get("/me", response_model=UserOut, summary="Mon compte et mes rôles")
def me(user: CurrentUser) -> UserOut:
    return service.user_out(user)


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