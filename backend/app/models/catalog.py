"""SA-12 — Catalogue académique : établissements, parcours, formations et informations associées.

Règle de traçabilité : chaque information du catalogue référence OBLIGATOIREMENT un
document source (source_documents : titre, type, version, date, hash).
"""

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.models.base import Base, DemoMixin, IdMixin, TimestampMixin, pg_enum


# --------------------------------------------------------------------------- ENUMs
class ProgramStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class StudyMode(str, enum.Enum):
    on_site = "on_site"
    hybrid = "hybrid"
    online = "online"
    work_study = "work_study"


class PrerequisiteKind(str, enum.Enum):
    diploma = "diploma"
    level = "level"
    subject = "subject"
    skill = "skill"


class AdmissionConditionKind(str, enum.Enum):
    dossier_review = "dossier_review"
    minimum_average = "minimum_average"
    entrance_exam = "entrance_exam"
    qcm = "qcm"
    interview = "interview"
    equivalence = "equivalence"
    other = "other"


class FeeType(str, enum.Enum):
    registration = "registration"
    tuition = "tuition"
    exam = "exam"
    other = "other"


class CampaignStatus(str, enum.Enum):
    planned = "planned"
    open = "open"
    closed = "closed"


class SourceDocumentType(str, enum.Enum):
    brochure = "brochure"
    faq = "faq"
    procedure = "procedure"
    programme = "programme"


class SourceDocumentStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    superseded = "superseded"
    archived = "archived"


ACADEMIC_YEAR_REGEX = r"^[0-9]{4}-[0-9]{4}$"


# --------------------------------------------------------------- Source documentaire
class SourceDocument(IdMixin, TimestampMixin, DemoMixin, Base):
    """Document officiel (brochure, FAQ, procédure, programme). Ancre de traçabilité + RAG (SA-14)."""

    __tablename__ = "source_documents"
    __table_args__ = (
        UniqueConstraint("title", "version"),
        UniqueConstraint("content_hash"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="content_hash_sha256"),
    )

    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[SourceDocumentType] = mapped_column(
        pg_enum(SourceDocumentType, "source_document_type"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    status: Mapped[SourceDocumentStatus] = mapped_column(
        pg_enum(SourceDocumentStatus, "source_document_status"),
        nullable=False,
        server_default=SourceDocumentStatus.draft.value,
    )
    uri: Mapped[str | None] = mapped_column(String(1024))  # chemin/URL du fichier d'origine
    language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="fr")
    document_date: Mapped[date | None] = mapped_column(Date)  # date d'édition du document
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    institution: Mapped["Institution | None"] = relationship(back_populates="source_documents")


class SourcedMixin:
    """Lien obligatoire vers le document source de l'information."""

    @declared_attr
    def source_document_id(cls) -> Mapped[int]:  # noqa: N805
        return mapped_column(
            BigInteger, ForeignKey("source_documents.id", ondelete="RESTRICT"), nullable=False, index=True
        )

    @declared_attr
    def source_document(cls) -> Mapped[SourceDocument]:  # noqa: N805
        return relationship(SourceDocument, lazy="joined")


# ------------------------------------------------------------------------ Catalogue
class Institution(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "institutions"
    __table_args__ = (CheckConstraint("code ~ '^[A-Z0-9_]{2,20}$'", name="code_format"),)

    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)  # IIT, ISB
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    programs: Mapped[list["Program"]] = relationship(back_populates="institution")
    source_documents: Mapped[list[SourceDocument]] = relationship(back_populates="institution")


class ProgramType(IdMixin, TimestampMixin, DemoMixin, Base):
    """Type de parcours : Licence, Préparatoire, Ingénierie, Master…"""

    __tablename__ = "program_types"
    __table_args__ = (CheckConstraint("code ~ '^[A-Z0-9_]{2,30}$'", name="code_format"),)

    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Program(IdMixin, TimestampMixin, DemoMixin, SourcedMixin, Base):
    """Formation / programme proposé par un établissement."""

    __tablename__ = "programs"
    __table_args__ = (
        CheckConstraint("duration_semesters BETWEEN 1 AND 12", name="duration_range"),
        CheckConstraint("code ~ '^[A-Z0-9_-]{2,40}$'", name="code_format"),
        CheckConstraint(
            "(status <> 'published') OR (published_at IS NOT NULL)", name="published_has_date"
        ),
        Index("ix_programs_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_programs_institution_status", "institution_id", "status"),
    )

    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    program_type_id: Mapped[int] = mapped_column(
        ForeignKey("program_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)  # contenu de la formation
    duration_semesters: Mapped[int] = mapped_column(Integer, nullable=False)
    study_mode: Mapped[StudyMode] = mapped_column(
        pg_enum(StudyMode, "study_mode"), nullable=False, server_default=StudyMode.on_site.value
    )
    teaching_language: Mapped[str] = mapped_column(String(50), nullable=False, server_default="fr")
    diploma_awarded: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ProgramStatus] = mapped_column(
        pg_enum(ProgramStatus, "program_status"),
        nullable=False,
        server_default=ProgramStatus.draft.value,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Recherche plein texte (français) maintenue par PostgreSQL.
    search_vector = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('french', coalesce(title,'') || ' ' || coalesce(summary,'') || ' ' || coalesce(description,''))",
            persisted=True,
        ),
    )

    institution: Mapped[Institution] = relationship(back_populates="programs", lazy="joined")
    program_type: Mapped[ProgramType] = relationship(lazy="joined")
    prerequisites: Mapped[list["ProgramPrerequisite"]] = relationship(
        back_populates="program", order_by="ProgramPrerequisite.position"
    )
    admission_conditions: Mapped[list["AdmissionCondition"]] = relationship(
        back_populates="program", order_by="AdmissionCondition.position"
    )
    career_outcomes: Mapped[list["CareerOutcome"]] = relationship(back_populates="program")
    tuition_fees: Mapped[list["TuitionFee"]] = relationship(back_populates="program")
    outgoing_pathways: Mapped[list["ProgramPathway"]] = relationship(
        foreign_keys="ProgramPathway.from_program_id", back_populates="from_program"
    )


class ProgramPrerequisite(IdMixin, TimestampMixin, DemoMixin, SourcedMixin, Base):
    __tablename__ = "program_prerequisites"
    __table_args__ = (UniqueConstraint("program_id", "label"),)

    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    kind: Mapped[PrerequisiteKind] = mapped_column(pg_enum(PrerequisiteKind, "prerequisite_kind"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    program: Mapped[Program] = relationship(back_populates="prerequisites")


class AdmissionCondition(IdMixin, TimestampMixin, DemoMixin, SourcedMixin, Base):
    __tablename__ = "admission_conditions"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", "position"),
        CheckConstraint(
            f"academic_year IS NULL OR academic_year ~ '{ACADEMIC_YEAR_REGEX}'", name="academic_year_format"
        ),
        CheckConstraint("minimum_average IS NULL OR minimum_average BETWEEN 0 AND 20", name="average_range"),
    )

    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year: Mapped[str | None] = mapped_column(String(9))  # NULL = valable toutes années
    kind: Mapped[AdmissionConditionKind] = mapped_column(
        pg_enum(AdmissionConditionKind, "admission_condition_kind"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    minimum_average: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))  # sur 20
    eligible_bac_sections: Mapped[list[str] | None] = mapped_column(ARRAY(String(50)))
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    program: Mapped[Program] = relationship(back_populates="admission_conditions")


class CareerOutcome(IdMixin, TimestampMixin, DemoMixin, SourcedMixin, Base):
    """Débouchés professionnels."""

    __tablename__ = "career_outcomes"
    __table_args__ = (UniqueConstraint("program_id", "title"),)

    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    program: Mapped[Program] = relationship(back_populates="career_outcomes")


class ProgramPathway(IdMixin, TimestampMixin, DemoMixin, SourcedMixin, Base):
    """Passerelle d'un parcours vers un autre (ex. Prépa -> Ingénierie)."""

    __tablename__ = "program_pathways"
    __table_args__ = (
        UniqueConstraint("from_program_id", "to_program_id"),
        CheckConstraint("from_program_id <> to_program_id", name="distinct_programs"),
    )

    from_program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry_level: Mapped[str | None] = mapped_column(String(100))  # ex. "Entrée en 1ère année"
    conditions: Mapped[str | None] = mapped_column(Text)

    from_program: Mapped[Program] = relationship(foreign_keys=[from_program_id], back_populates="outgoing_pathways")
    to_program: Mapped[Program] = relationship(foreign_keys=[to_program_id], lazy="joined")


class TuitionFee(IdMixin, TimestampMixin, DemoMixin, SourcedMixin, Base):
    __tablename__ = "tuition_fees"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year", "fee_type"),
        CheckConstraint(f"academic_year ~ '{ACADEMIC_YEAR_REGEX}'", name="academic_year_format"),
        CheckConstraint("amount >= 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso4217"),
        Index("ix_tuition_fees_program_year", "program_id", "academic_year"),
    )

    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False
    )
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)  # "2026-2027"
    fee_type: Mapped[FeeType] = mapped_column(pg_enum(FeeType, "fee_type"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)  # TND : 3 décimales
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="TND")
    payment_terms: Mapped[str | None] = mapped_column(Text)

    program: Mapped[Program] = relationship(back_populates="tuition_fees")


class AdmissionCampaign(IdMixin, TimestampMixin, DemoMixin, SourcedMixin, Base):
    __tablename__ = "admission_campaigns"
    __table_args__ = (
        UniqueConstraint("institution_id", "academic_year", "name"),
        CheckConstraint(f"academic_year ~ '{ACADEMIC_YEAR_REGEX}'", name="academic_year_format"),
        CheckConstraint("closes_at > opens_at", name="dates_order"),
    )

    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        pg_enum(CampaignStatus, "campaign_status"), nullable=False, server_default=CampaignStatus.planned.value
    )

    institution: Mapped[Institution] = relationship()
