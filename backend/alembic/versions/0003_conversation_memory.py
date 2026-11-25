"""SA-37 — mémoire conversationnelle : profil candidat mémorisé par conversation.

Ajoute ``conversations.memory`` (JSONB) : profil (niveau, section du bac, moyenne, intérêts,
préférences, contraintes, projet, formations évoquées), dernières questions, langue et nombre de tours.
Les messages eux-mêmes restent dans ``messages`` (mémoire courte).

Revision ID: 0003_conversation_memory
Revises: 0002_ai_views_and_grants
Create Date: 2026-11-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_conversation_memory"
down_revision: str | None = "0002_ai_views_and_grants"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("memory", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"),
                  nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_conversations_memory_is_object"), "conversations", "jsonb_typeof(memory) = 'object'"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_conversations_memory_is_object"), "conversations", type_="check")
    op.drop_column("conversations", "memory")
