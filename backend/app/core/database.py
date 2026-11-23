"""Engines et sessions SQLAlchemy.

- engine applicatif : rôle smartcampus_app (DML limité, sans DELETE) ;
- engine IA : rôle ai_readonly (vues ai_views uniquement), utilisé par app.core.ai_sql.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)


@lru_cache
def get_ai_engine() -> Engine:
    return create_engine(get_settings().ai_readonly_database_url, pool_pre_ping=True, pool_size=2, max_overflow=2)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()
