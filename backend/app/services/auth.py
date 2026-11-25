"""SA-28 — Authentification (inscription, connexion, JWT) et gestion des rôles."""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError, UnprocessableError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import AuditLog, Candidate, Role, User, UserRole
from app.models.identity import RoleCode
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut

INVALID_CREDENTIALS = "Email ou mot de passe incorrect."


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=sorted(code.value for code in user.role_codes),
    )


def issue_token(user: User) -> TokenResponse:
    minutes = get_settings().jwt_access_token_expire_minutes
    token = create_access_token(user.id, [code.value for code in user.role_codes], minutes)
    return TokenResponse(access_token=token, expires_in=minutes * 60, user=user_out(user))


def _audit(db: Session, actor_id: int, action: str, user: User, details: dict | None = None) -> None:
    db.add(
        AuditLog(
            actor_type="user",
            actor_user_id=actor_id,
            action=action,
            entity_type="users",
            entity_id=user.id,
            details=details,
        )
    )


def _get_role(db: Session, code: RoleCode) -> Role:
    role = db.scalars(select(Role).where(Role.code == code)).one_or_none()
    if role is None:
        raise UnprocessableError(f"Rôle inconnu en base : {code.value}.")
    return role


def register_candidate(db: Session, payload: RegisterRequest) -> User:
    email = _normalize_email(payload.email)
    if db.scalars(select(User.id).where(User.email == email)).first() is not None:
        raise ConflictError("Un compte existe déjà avec cet email.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=f"{payload.first_name.strip()} {payload.last_name.strip()}",
    )
    db.add(user)
    db.flush()  # obtient user.id
    db.add(UserRole(user_id=user.id, role_id=_get_role(db, RoleCode.candidate).id))
    db.add(Candidate(user_id=user.id, first_name=payload.first_name.strip(), last_name=payload.last_name.strip()))
    _audit(db, user.id, "auth.register", user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Un compte existe déjà avec cet email.") from None
    db.expire(user)  # recharge user.roles
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalars(select(User).where(User.email == _normalize_email(email))).one_or_none()
    # Même message dans tous les cas : on ne révèle pas si l'email existe.
    if user is None or not user.is_active or not user.password_hash:
        raise UnauthorizedError(INVALID_CREDENTIALS)
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError(INVALID_CREDENTIALS)
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return user


def set_user_roles(db: Session, admin: User, user_id: int, codes: list[RoleCode]) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Utilisateur introuvable.")
    wanted = set(codes)
    if user.id == admin.id and RoleCode.admin not in wanted:
        raise UnprocessableError("Un administrateur ne peut pas retirer son propre rôle admin.")

    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    for code in sorted(wanted, key=lambda c: c.value):
        db.add(UserRole(user_id=user.id, role_id=_get_role(db, code).id, granted_by=admin.id))
    _audit(db, admin.id, "user.roles.update", user, {"roles": sorted(c.value for c in wanted)})
    db.commit()
    db.expire(user)
    return user