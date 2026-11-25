"""Configuration centralisée (lue depuis les variables d'environnement / .env)."""

from functools import lru_cache
from typing import Literal

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
    
    # SA-25 : durée de vie d'une session visiteur, comptée depuis la dernière activité.
    guest_session_ttl_hours: int = Field(default=24, ge=1, le=720)

    # Dimension des embeddings pgvector (doit correspondre au modèle choisi par l'équipe RAG).
    embedding_dim: int = 1024

    # --- LLM (epic SA-30) : serveur OpenAI-compatible (Ollama, vLLM, TGI...). Choix du modèle : docs/llm_selection.md
    llm_provider: Literal["openai_compatible", "fake"] = "openai_compatible"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_api_key: str | None = None
    llm_timeout_s: float = Field(default=60.0, gt=0, le=600)
    llm_temperature: float = Field(default=0.3, ge=0, le=2)
    llm_max_tokens: int = Field(default=512, ge=16, le=8192)
    # Mémoire conversationnelle (SA-37) : fenêtre d'historique envoyée au LLM + profil candidat mémorisé.
    llm_memory_max_messages: int = Field(default=12, ge=2, le=100)
    llm_memory_max_chars: int = Field(default=6000, ge=500, le=100_000)
    llm_memory_extraction: Literal["regles", "llm"] = "regles"
    chat_message_max_chars: int = Field(default=2000, ge=50, le=10_000)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
