"""SA-14 — Documents sources (RAG) et synchronisation.

source_documents est défini dans catalog.py (c'est l'ancre de traçabilité du catalogue) ;
ce module ajoute les chunks vectorisés (pgvector) et les traces de synchronisation.
"""

import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, DemoMixin, IdMixin, TimestampMixin, pg_enum

# Doit correspondre au modèle d'embedding retenu par l'équipe RAG (ex. bge-m3 / multilingual-e5-large).
# Changer cette valeur impose une nouvelle migration (ALTER TYPE vector(n)) et une ré-indexation.
EMBEDDING_DIM = 1024


class SyncJobType(str, enum.Enum):
    ingest = "ingest"          # nouveau document
    reindex = "reindex"        # recalcul des embeddings
    full_sync = "full_sync"    # resynchronisation complète


class SyncStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    partial = "partial"


class SyncLogLevel(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"


class DocumentChunk(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("source_document_id", "chunk_index"),
        CheckConstraint("chunk_index >= 0", name="chunk_index_positive"),
        CheckConstraint("token_count IS NULL OR token_count > 0", name="token_count_positive"),
        # Recherche de similarité cosinus (HNSW, pgvector >= 0.5).
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    source_document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Formation concernée (NULL = chunk général : FAQ, procédure transverse…).
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(255))  # pour citer précisément la source
    page_number: Mapped[int | None] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding = mapped_column(Vector(EMBEDDING_DIM))  # NULL tant que non vectorisé
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    chunk_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)

    source_document = relationship("SourceDocument")


class SyncJob(IdMixin, TimestampMixin, Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        CheckConstraint("finished_at IS NULL OR started_at IS NOT NULL", name="finished_after_start"),
        CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="dates_order"),
        CheckConstraint("error_count >= 0 AND processed_count >= 0", name="counters_positive"),
        CheckConstraint(
            "status NOT IN ('succeeded', 'failed', 'partial') OR finished_at IS NOT NULL",
            name="terminal_has_end",
        ),
        Index("ix_sync_jobs_status_created", "status", "created_at"),
    )

    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_documents.id", ondelete="RESTRICT"), index=True
    )  # NULL = job global
    job_type: Mapped[SyncJobType] = mapped_column(pg_enum(SyncJobType, "sync_job_type"), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(pg_enum(SyncStatus, "sync_status"), nullable=False, server_default="pending")
    triggered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)

    logs: Mapped[list["SyncLog"]] = relationship(back_populates="job", order_by="SyncLog.id")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sync_job_id: Mapped[int] = mapped_column(ForeignKey("sync_jobs.id", ondelete="RESTRICT"), nullable=False, index=True)
    level: Mapped[SyncLogLevel] = mapped_column(pg_enum(SyncLogLevel, "sync_log_level"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    job: Mapped[SyncJob] = relationship(back_populates="logs")
