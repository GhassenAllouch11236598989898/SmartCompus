"""SA-16 — Garde-fou de l'outil SQL de l'agent IA (le LLM génère le SQL, le backend le contrôle).

Défense en profondeur :
1. validation syntaxique : une seule requête SELECT/WITH, sans commentaire ni ';' interne,
   sans fonction dangereuse ni accès aux catalogues système ;
2. encapsulation : SELECT * FROM (<requête>) LIMIT n  => LIMIT imposé, aucune instruction
   non-SELECT possible (un CTE modifiant doit être au niveau supérieur) ;
3. transaction READ ONLY + SET LOCAL statement_timeout ;
4. rôle PostgreSQL ai_readonly : SELECT sur ai_views uniquement, aucun droit sur public
   (tables sensibles : users.password_hash, consents, conversations.session_token_hash…).
"""

import re
from typing import Any

from sqlalchemy import Engine, text

from app.core.config import get_settings


class UnsafeAiQueryError(ValueError):
    """Requête générée par l'IA refusée par le garde-fou."""


_FORBIDDEN = re.compile(
    r"\b(pg_sleep\w*|set_config|current_setting|pg_read\w*|pg_ls\w*|pg_stat\w*|lo_\w+|dblink\w*"
    r"|pg_terminate_backend|pg_cancel_backend|pg_catalog|information_schema|pg_\w*class|pg_roles|pg_user\w*"
    r"|pg_shadow|pg_authid|copy|into|public)\b",
    re.IGNORECASE,
)
_STARTS_WITH_SELECT = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


def validate_ai_sql(sql: str) -> str:
    """Retourne la requête nettoyée ou lève UnsafeAiQueryError."""
    if not sql or not sql.strip():
        raise UnsafeAiQueryError("requête vide")
    cleaned = sql.strip().rstrip(";").strip()
    if len(cleaned) > 4000:
        raise UnsafeAiQueryError("requête trop longue")
    if ";" in cleaned:
        raise UnsafeAiQueryError("une seule instruction autorisée")
    if "--" in cleaned or "/*" in cleaned:
        raise UnsafeAiQueryError("commentaires SQL interdits")
    if not _STARTS_WITH_SELECT.match(cleaned):
        raise UnsafeAiQueryError("seules les requêtes SELECT sont autorisées")
    match = _FORBIDDEN.search(cleaned)
    if match:
        raise UnsafeAiQueryError(f"élément interdit : {match.group(0)}")
    return cleaned


def run_ai_query(
    sql: str,
    params: dict[str, Any] | None = None,
    *,
    engine: Engine | None = None,
    max_rows: int | None = None,
) -> list[dict[str, Any]]:
    """Exécute une requête de l'agent IA sous le rôle ai_readonly avec LIMIT et timeout imposés."""
    settings = get_settings()
    if engine is None:
        from app.core.database import get_ai_engine

        engine = get_ai_engine()
    limit = min(max_rows or settings.ai_sql_max_rows, settings.ai_sql_max_rows)
    safe_sql = validate_ai_sql(sql)
    bound = dict(params or {})
    if "_ai_limit" in bound:
        raise UnsafeAiQueryError("paramètre réservé")
    bound["_ai_limit"] = limit
    wrapped = text(f"SELECT * FROM ({safe_sql}) AS ai_query LIMIT :_ai_limit")
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text(f"SET LOCAL statement_timeout = {int(settings.ai_sql_statement_timeout_ms)}"))
            rows = conn.execute(wrapped, bound).mappings().all()
    return [dict(r) for r in rows]
