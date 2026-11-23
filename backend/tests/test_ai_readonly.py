"""SA-16 — rôle ai_readonly, vues ai_views et garde-fou SQL de l'agent IA."""

import pytest
from psycopg import errors as pg
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from app.core.ai_sql import UnsafeAiQueryError, run_ai_query, validate_ai_sql


def test_ai_can_read_public_views(ai_engine: Engine):
    rows = run_ai_query("SELECT code, title, source_title FROM v_formations_public ORDER BY code", engine=ai_engine)
    codes = [r["code"] for r in rows]
    assert "IIT-ING-GI" in codes
    assert "IIT-ING-GC" not in codes  # brouillon jamais exposé
    assert all(r["source_title"] for r in rows)


def test_limit_is_enforced(ai_engine: Engine):
    rows = run_ai_query("SELECT * FROM v_tuition_fees_public LIMIT 1000", engine=ai_engine, max_rows=3)
    assert len(rows) == 3


def test_parameters_are_bound(ai_engine: Engine):
    rows = run_ai_query(
        "SELECT dossier_id, dossier_status FROM v_candidate_dossier_summary WHERE last_decision = :d",
        {"d": "admitted"},
        engine=ai_engine,
    )
    assert len(rows) == 1


@pytest.mark.parametrize("table", ["users", "consents", "conversations", "messages", "candidates", "audit_log",
                                   "public.users", "programs"])
def test_ai_cannot_read_tables(ai_engine: Engine, table: str):
    with ai_engine.connect() as conn, pytest.raises(DBAPIError) as exc:
        conn.execute(text(f"SELECT * FROM {table} LIMIT 1"))
    assert isinstance(exc.value.orig, (pg.InsufficientPrivilege, pg.UndefinedTable))


@pytest.mark.parametrize("sql", [
    "INSERT INTO ai_views.v_formations_public (code) VALUES ('X')",
    "UPDATE ai_views.v_formations_public SET title = 'x'",
    "CREATE TABLE ai_views.t (id int)",
])
def test_ai_cannot_write(ai_engine: Engine, sql: str):
    with ai_engine.connect() as conn, pytest.raises(DBAPIError) as exc:
        conn.execute(text(sql))
    assert isinstance(exc.value.orig, (pg.ReadOnlySqlTransaction, pg.InsufficientPrivilege, pg.ObjectNotInPrerequisiteState))


def test_ai_role_session_defaults(ai_engine: Engine):
    with ai_engine.connect() as conn:
        assert conn.execute(text("SHOW statement_timeout")).scalar_one() == "3s"
        assert conn.execute(text("SHOW default_transaction_read_only")).scalar_one() == "on"
        assert conn.execute(text("SHOW search_path")).scalar_one() == "ai_views"


def test_statement_timeout_cancels_long_query(ai_engine: Engine):
    with ai_engine.connect() as conn, pytest.raises(DBAPIError) as exc:
        conn.execute(text("SET statement_timeout = 200"))
        conn.execute(text("SELECT pg_sleep(2)"))
    assert isinstance(exc.value.orig, pg.QueryCanceled)


@pytest.mark.parametrize("sql", [
    "",
    "DELETE FROM v_formations_public",
    "SELECT 1; DROP TABLE users",
    "SELECT 1 -- commentaire",
    "SELECT /* x */ 1",
    "SELECT pg_sleep(10)",
    "SELECT set_config('statement_timeout', '0', false)",
    "SELECT * FROM public.users",
    "SELECT * FROM pg_catalog.pg_roles",
    "SELECT * FROM information_schema.tables",
    "SELECT * INTO nouvelle FROM v_formations_public",
    "COPY users TO '/tmp/x'",
    "SELECT " + "x," * 3000 + "1",
])
def test_guard_rejects_unsafe_sql(sql: str):
    with pytest.raises(UnsafeAiQueryError):
        validate_ai_sql(sql)


def test_guard_accepts_select_and_cte():
    assert validate_ai_sql("SELECT 1;") == "SELECT 1"
    assert validate_ai_sql("WITH x AS (SELECT 1 AS a) SELECT a FROM x").startswith("WITH")


def test_reserved_parameter_rejected(ai_engine: Engine):
    with pytest.raises(UnsafeAiQueryError):
        run_ai_query("SELECT 1 AS a", {"_ai_limit": 5}, engine=ai_engine)
