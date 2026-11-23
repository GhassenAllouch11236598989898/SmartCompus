"""SA-13 — Utilisateurs et rôles (RBAC).

Le périmètre d'un responsable est porté par roles.institution_id :
responsable_iit -> IIT, responsable_isb -> ISB, responsable_entretien -> NULL (périmètre = entretiens).
"""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, DemoMixin, IdMixin, TimestampMixin, pg_enum


class RoleCode(str, enum.Enum):
    candidate = "candidate"
    responsable_iit = "responsable_iit"
    responsable_isb = "responsable_isb"
    responsable_entretien = "responsable_entretien"
    direction = "direction"
    admin = "admin"


RESPONSABLE_ROLES = frozenset(
    {RoleCode.responsable_iit, RoleCode.responsable_isb, RoleCode.responsable_entretien}
)


class Role(IdMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    code: Mapped[RoleCode] = mapped_column(pg_enum(RoleCode, "role_code"), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # Périmètre établissement du rôle (NULL = transverse).
    institution_id: Mapped[int | None] = mapped_column(ForeignKey("institutions.id", ondelete="RESTRICT"))


class User(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("position('@' in email) > 1", name="email_format"),
        # Hash bcrypt/argon2 uniquement, jamais de mot de passe en clair.
        CheckConstraint("password_hash IS NULL OR password_hash ~ '^\\$(2[aby]|argon2id?)\\$'", name="password_hashed"),
        CheckConstraint("NOT is_service_account OR password_hash IS NULL", name="service_account_no_password"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # Compte technique (ex. agent IA) : ne peut JAMAIS prendre de décision officielle.
    is_service_account: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Jointure explicite : user_roles.granted_by référence aussi users.
    roles: Mapped[list[Role]] = relationship(
        secondary="user_roles",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id",
        lazy="selectin",
        viewonly=True,
    )

    @property
    def role_codes(self) -> set[RoleCode]:
        return {r.code for r in self.roles}


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (Index("ix_user_roles_role_id", "role_id"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    granted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
