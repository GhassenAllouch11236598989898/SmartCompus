"""Fixtures de test : base PostgreSQL réelle (smartcampus_test), migrations, seed et client HTTP.

- Une fois par session : alembic downgrade base -> upgrade head, puis seed exécuté DEUX fois
  (les comptages après chaque passage servent au test d'idempotence).
- Chaque test s'exécute dans une transaction annulée à la fin (isolation), via le rôle
  applicatif smartcampus_app : les tests vérifient donc aussi ses privilèges réels.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine, func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.main import create_app
from app.models import Base, User
from seeds.seed import run_seed


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    test_database_url: str = "postgresql+psycopg://smartcampus_app:change_me_app@localhost:5434/smartcampus_test"
    test_migration_database_url: str = (
        "postgresql+psycopg://smartcampus_owner:change_me_owner@localhost:5434/smartcampus_test"
    )
    test_ai_readonly_database_url: str = "postgresql+psycopg://ai_readonly:change_me_ai@localhost:5434/smartcampus_test"


SETTINGS = TestSettings()


def _alembic_config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.attributes["configure_logger"] = False
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def table_counts(engine: Engine) -> dict[str, int]:
    with engine.connect() as conn:
        return {t: conn.execute(select(func.count()).select_from(Base.metadata.tables[t])).scalar_one()
                for t in Base.metadata.tables}


@pytest.fixture(scope="session")
def owner_engine() -> Iterator[Engine]:
    engine = create_engine(SETTINGS.test_migration_database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - message d'aide
        pytest.exit(f"Base de test injoignable ({type(exc).__name__}). Lancer : docker compose up -d postgres", 2)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def migration_report(owner_engine: Engine) -> dict:
    cfg = _alembic_config(SETTINGS.test_migration_database_url)
    command.downgrade(cfg, "base")
    with owner_engine.connect() as conn:
        tables_after_downgrade = conn.execute(
            text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name <> 'alembic_version'")
        ).scalar_one()
    command.upgrade(cfg, "head")
    # Cycle complet : prouve que downgrade/upgrade sont rejouables sur une base déjà migrée.
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    with Session(owner_engine) as s, s.begin():
        run_seed(s)
    counts_first = table_counts(owner_engine)
    with Session(owner_engine) as s, s.begin():
        run_seed(s)
    counts_second = table_counts(owner_engine)
    return {
        "tables_after_downgrade": tables_after_downgrade,
        "counts_first": counts_first,
        "counts_second": counts_second,
    }


@pytest.fixture(scope="session")
def app_engine(migration_report: dict) -> Iterator[Engine]:
    engine = create_engine(SETTINGS.test_database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def ai_engine(migration_report: dict) -> Iterator[Engine]:
    engine = create_engine(SETTINGS.test_ai_readonly_database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def db(app_engine: Engine) -> Iterator[Session]:
    """Session du rôle applicatif, dans une transaction annulée à la fin du test."""
    conn = app_engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture
def owner_db(owner_engine: Engine, migration_report: dict) -> Iterator[Session]:
    conn = owner_engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    trans.rollback()
    conn.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


DEMO = "demo.smartcampus.invalid"


@pytest.fixture
def user_by_email(db: Session):
    def _get(local: str) -> User:
        return db.scalars(select(User).where(User.email == f"{local}@{DEMO}")).one()

    return _get


@pytest.fixture
def auth(user_by_email):
    """auth('admin') -> en-têtes Authorization pour un utilisateur de démo."""

    def _headers(local: str) -> dict[str, str]:
        user = user_by_email(local)
        return {"Authorization": f"Bearer {create_access_token(user.id, [r.code.value for r in user.roles])}"}

    return _headers


@pytest.fixture
def program_id(db: Session):
    from app.models import Program

    def _get(code: str) -> int:
        return db.scalars(select(Program.id).where(Program.code == code)).one()

    return _get
