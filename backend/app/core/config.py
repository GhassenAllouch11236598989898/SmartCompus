"""Configuration centralisée (lue depuis les variables d'environnement / .env)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SmartCampus AI API"
    environment: str = "development"

    # Connexion de l'API (rôle applicatif à droits limités : pas de DDL, pas de DELETE).
    database_url: str = "postgresql+psycopg://smartcampus_app:change_me_app@localhost:5434/smartcampus"
    # Connexion propriétaire du schéma : migrations Alembic et seed uniquement.
    migration_database_url: str = "postgresql+psycopg://smartcampus_owner:change_me_owner@localhost:5434/smartcampus"
    # Connexion de l'outil SQL de l'agent IA (schéma ai_views en lecture seule).
    ai_readonly_database_url: str = "postgresql+psycopg://ai_readonly:change_me_ai@localhost:5434/smartcampus"
    ai_sql_max_rows: int = Field(default=100, ge=1, le=1000)
    ai_sql_statement_timeout_ms: int = Field(default=3000, ge=100, le=30000)

    # JWT minimal (émission hors périmètre SA-10 : voir scripts/issue_token.py).
    jwt_secret_key: str = "dev-only-change-me-please-32-chars-min"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:3000"

    # Dimension des embeddings pgvector (doit correspondre au modèle choisi par l'équipe RAG).
    embedding_dim: int = 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
