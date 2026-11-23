"""Base déclarative SQLAlchemy, conventions de nommage et mixins communs."""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Identity, MetaData, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Noms de contraintes déterministes => migrations Alembic reproductibles.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """ENUM PostgreSQL natif stockant les *valeurs* (minuscules) de l'Enum Python."""
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class IdMixin:
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True, sort_order=-100)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), sort_order=100
    )
    # Maintenu aussi par le trigger SQL set_updated_at() (voir migration).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), sort_order=101
    )


class DemoMixin:
    # true = donnée FICTIVE de démonstration (voir SEED_DATA_NOTES.md) à remplacer.
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), sort_order=102)
