"""Dépendances FastAPI : session DB, utilisateur courant (JWT) et contrôle de rôle (RBAC minimal)."""

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import User
from app.models.identity import RoleCode

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False, description="JWT d'accès (émis par l'epic Auth ; en dev : scripts/issue_token.py)")


def _load_user(db: Session, credentials: HTTPAuthorizationCredentials | None) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise UnauthorizedError("Jeton d'accès invalide ou expiré.") from None
    # Les rôles sont relus en base (source de vérité), pas depuis le jeton.
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Compte inexistant ou désactivé.")
    return user


def get_optional_user(
    db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User | None:
    return _load_user(db, credentials)


def get_current_user(
    db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    user = _load_user(db, credentials)
    if user is None:
        raise UnauthorizedError("Authentification requise.")
    return user


def require_roles(*roles: RoleCode) -> Callable[[User], User]:
    allowed = set(roles)

    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not (user.role_codes & allowed):
            raise ForbiddenError("Rôle insuffisant pour cette action.")
        return user

    return checker


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
CatalogManager = Annotated[
    User, Depends(require_roles(RoleCode.admin, RoleCode.responsable_iit, RoleCode.responsable_isb))
]
