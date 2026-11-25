"""SA-13 — Candidats, conversations, recommandations, dossiers de candidature et suivi.

Règles portées par la base (voir migration 0001) :
- aucune suppression physique (trigger prevent_delete + rôle applicatif sans DELETE) ;
- historique automatique des changements de statut (status_history) ;
- decisions / revues : uniquement par un utilisateur humain ayant un rôle responsable
  (trigger assert_human_responsable) — un agent IA ne peut jamais en créer.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, DemoMixin, IdMixin, TimestampMixin, pg_enum


# --------------------------------------------------------------------------- ENUMs
class EducationLevel(str, enum.Enum):
    lycee = "lycee"                # élève de terminale
    bac = "bac"                    # bachelier
    bac_plus_1 = "bac_plus_1"
    bac_plus_2 = "bac_plus_2"
    bac_plus_3 = "bac_plus_3"
    bac_plus_4_or_more = "bac_plus_4_or_more"
    other = "other"


class ConversationStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class MessageSender(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageChannel(str, enum.Enum):
    text = "text"
    audio = "audio"


class MessageLanguage(str, enum.Enum):
    fr = "fr"
    ar = "ar"                    # arabe standard
    tn_darija = "tn_darija"      # dialecte tunisien (graphie arabe)
    arabizi = "arabizi"          # dialecte tunisien en caractères latins/chiffres
    en = "en"
    mixed = "mixed"
    unknown = "unknown"


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    adjusted = "adjusted"


class ConsentType(str, enum.Enum):
    data_processing = "data_processing"
    ai_processing = "ai_processing"
    audio_recording = "audio_recording"
    email_notifications = "email_notifications"


class DossierStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    interview_scheduled = "interview_scheduled"
    decision_pending = "decision_pending"
    decided = "decided"
    enrolled = "enrolled"
    withdrawn = "withdrawn"
    closed = "closed"


# Statuts "terminés" : hors de la contrainte "un dossier actif par candidat et campagne".
DOSSIER_FINAL_STATUSES = ("enrolled", "withdrawn", "closed")


class PreinscriptionStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    under_review = "under_review"
    validated = "validated"
    rejected = "rejected"
    cancelled = "cancelled"


class EquivalenceStatus(str, enum.Enum):
    submitted = "submitted"
    under_review = "under_review"
    accepted = "accepted"
    rejected = "rejected"
    more_info_requested = "more_info_requested"


class EquivalenceDocumentType(str, enum.Enum):
    diploma = "diploma"
    transcript = "transcript"
    syllabus = "syllabus"
    identity = "identity"
    other = "other"


class QcmGeneratedBy(str, enum.Enum):
    ai = "ai"
    template = "template"


class QcmStatus(str, enum.Enum):
    generated = "generated"
    in_progress = "in_progress"
    completed = "completed"
    expired = "expired"


class AppointmentMode(str, enum.Enum):
    on_site = "on_site"
    online = "online"
    phone = "phone"


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class InterviewOpinion(str, enum.Enum):
    favorable = "favorable"
    reserved = "reserved"
    unfavorable = "unfavorable"


class DecisionValue(str, enum.Enum):
    admitted = "admitted"
    admitted_with_conditions = "admitted_with_conditions"
    waitlisted = "waitlisted"
    rejected = "rejected"


class NotificationKind(str, enum.Enum):
    reminder = "reminder"
    confirmation = "confirmation"
    appointment = "appointment"
    decision = "decision"
    other = "other"


class NotificationChannel(str, enum.Enum):
    email = "email"
    in_app = "in_app"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class ActorType(str, enum.Enum):
    user = "user"
    ai_agent = "ai_agent"
    system = "system"


# ------------------------------------------------------------------- Candidats
class Candidate(IdMixin, TimestampMixin, DemoMixin, Base):
    """Identité minimale du candidat (minimisation des données personnelles)."""

    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint("birth_year IS NULL OR birth_year BETWEEN 1950 AND 2020", name="birth_year_range"),
        CheckConstraint("phone IS NULL OR phone ~ '^\\+?[0-9 ]{8,20}$'", name="phone_format"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)  # année seule : minimisation
    governorate: Mapped[str | None] = mapped_column(String(100))

    user = relationship("User")
    profile: Mapped["CandidateProfile | None"] = relationship(back_populates="candidate", uselist=False)


class CandidateProfile(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (
        CheckConstraint("bac_average IS NULL OR bac_average BETWEEN 0 AND 20", name="bac_average_range"),
        CheckConstraint("bac_year IS NULL OR bac_year BETWEEN 1980 AND 2100", name="bac_year_range"),
    )

    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    education_level: Mapped[EducationLevel | None] = mapped_column(pg_enum(EducationLevel, "education_level"))
    bac_section: Mapped[str | None] = mapped_column(String(50))  # ex. "Mathématiques", "Informatique"
    bac_year: Mapped[int | None] = mapped_column(SmallInteger)
    bac_average: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    current_program: Mapped[str | None] = mapped_column(String(255))  # parcours actuel (réorientation)
    interests: Mapped[list[str]] = mapped_column(ARRAY(String(100)), nullable=False, server_default="{}")
    preferred_subjects: Mapped[list[str]] = mapped_column(ARRAY(String(100)), nullable=False, server_default="{}")
    goals: Mapped[str | None] = mapped_column(Text)
    constraints: Mapped[str | None] = mapped_column(Text)  # budget, mobilité, horaires…
    preferred_language: Mapped[MessageLanguage | None] = mapped_column(pg_enum(MessageLanguage, "message_language"))

    candidate: Mapped[Candidate] = relationship(back_populates="profile")


# ---------------------------------------------------------------- Conversations
class Conversation(IdMixin, TimestampMixin, DemoMixin, Base):
    """Conversation chatbot. Visiteur anonyme : candidate_id NULL, identifié par session_token_hash.
    À la création du compte, candidate_id est renseigné (attached_at)."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint("candidate_id IS NULL OR attached_at IS NOT NULL", name="attached_has_date"),
        CheckConstraint("session_token_hash ~ '^[0-9a-f]{64}$'", name="session_token_sha256"),
        CheckConstraint("jsonb_typeof(memory) = 'object'", name="memory_is_object"),
    )

    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id", ondelete="RESTRICT"), index=True)
    # SHA-256 du jeton de session : le jeton brut n'est jamais stocké.
    session_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[ConversationStatus] = mapped_column(
        pg_enum(ConversationStatus, "conversation_status"), nullable=False, server_default="active"
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # SA-37 — mémoire longue du chatbot (profil candidat, questions posées, langue) : voir app/llm/memory.py.
    memory: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.sequence")


class Message(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
        CheckConstraint("channel <> 'audio' OR audio_uri IS NOT NULL", name="audio_has_uri"),
        CheckConstraint(
            "language_confidence IS NULL OR language_confidence BETWEEN 0 AND 1", name="confidence_range"
        ),
    )

    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    sender: Mapped[MessageSender] = mapped_column(pg_enum(MessageSender, "message_sender"), nullable=False)
    channel: Mapped[MessageChannel] = mapped_column(
        pg_enum(MessageChannel, "message_channel"), nullable=False, server_default="text"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)  # texte ou transcription Whisper
    detected_language: Mapped[MessageLanguage] = mapped_column(
        pg_enum(MessageLanguage, "message_language"), nullable=False, server_default="unknown"
    )
    language_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    audio_uri: Mapped[str | None] = mapped_column(String(1024))
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


# -------------------------------------------------------------- Recommandations
class Recommendation(IdMixin, TimestampMixin, DemoMixin, Base):
    """Recommandation de formation produite par l'agent IA, à valider par un responsable."""

    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint("candidate_id IS NOT NULL OR conversation_id IS NOT NULL", name="has_subject"),
        CheckConstraint("compatibility_score BETWEEN 0 AND 100", name="score_range"),
        CheckConstraint("rank BETWEEN 1 AND 3", name="rank_range"),
        CheckConstraint(
            "(review_status = 'pending' AND reviewed_by IS NULL AND reviewed_at IS NULL)"
            " OR (review_status <> 'pending' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="review_consistency",
        ),
        CheckConstraint("review_status <> 'adjusted' OR review_comment IS NOT NULL", name="adjusted_has_comment"),
        Index("ix_recommendations_review_status", "review_status"),
    )

    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id", ondelete="RESTRICT"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="RESTRICT"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    compatibility_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    # Sources citées par le RAG (ids de document_chunks / source_documents).
    cited_sources: Mapped[list | None] = mapped_column(JSONB)
    model_name: Mapped[str | None] = mapped_column(String(100))
    review_status: Mapped[ReviewStatus] = mapped_column(
        pg_enum(ReviewStatus, "review_status"), nullable=False, server_default="pending"
    )
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(Text)

    program = relationship("Program")


# ------------------------------------------------------------------ Consentements
class Consent(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint("user_id IS NOT NULL OR conversation_id IS NOT NULL", name="has_subject"),
        CheckConstraint("revoked_at IS NULL OR revoked_at >= granted_at", name="revocation_after_grant"),
        Index("ix_consents_user_type", "user_id", "consent_type"),
    )

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="RESTRICT"), index=True)
    consent_type: Mapped[ConsentType] = mapped_column(pg_enum(ConsentType, "consent_type"), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(20), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ------------------------------------------------------------------------ Dossiers
class Dossier(IdMixin, TimestampMixin, DemoMixin, Base):
    """Dossier de candidature : regroupe préinscriptions, équivalences, QCM, rendez-vous, décisions.
    Le périmètre établissement se déduit de la campagne (admission_campaigns.institution_id)."""

    __tablename__ = "dossiers"
    __table_args__ = (
        CheckConstraint(
            "(ai_summary IS NULL) = (ai_summary_updated_at IS NULL)", name="ai_summary_has_date"
        ),
        # Un seul dossier ACTIF par candidat et par campagne.
        Index(
            "uq_dossiers_active_candidate_campaign",
            "candidate_id",
            "campaign_id",
            unique=True,
            postgresql_where=text("status NOT IN ('enrolled', 'withdrawn', 'closed')"),
        ),
        Index("ix_dossiers_campaign_status", "campaign_id", "status"),
    )

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False, index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("admission_campaigns.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[DossierStatus] = mapped_column(
        pg_enum(DossierStatus, "dossier_status"), nullable=False, server_default="open"
    )
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_summary_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    candidate: Mapped[Candidate] = relationship()
    campaign = relationship("AdmissionCampaign")


class Preinscription(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "preinscriptions"
    __table_args__ = (
        UniqueConstraint("dossier_id", "program_id"),
        CheckConstraint("status = 'draft' OR submitted_at IS NOT NULL", name="submitted_has_date"),
        Index("ix_preinscriptions_status", "status"),
    )

    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False, index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[PreinscriptionStatus] = mapped_column(
        pg_enum(PreinscriptionStatus, "preinscription_status"), nullable=False, server_default="draft"
    )
    choice_rank: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EquivalenceRequest(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "equivalence_requests"
    __table_args__ = (
        CheckConstraint(
            "status NOT IN ('accepted', 'rejected', 'more_info_requested')"
            " OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="reviewed_when_decided",
        ),
        Index("ix_equivalence_requests_status", "status"),
    )

    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False, index=True)
    target_program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), nullable=False, index=True)
    origin_diploma: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_program: Mapped[str | None] = mapped_column(String(255))
    origin_institution: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_country: Mapped[str] = mapped_column(String(2), nullable=False, server_default="TN")  # ISO 3166-1
    origin_level: Mapped[EducationLevel | None] = mapped_column(pg_enum(EducationLevel, "education_level"))
    requested_entry_level: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[EquivalenceStatus] = mapped_column(
        pg_enum(EquivalenceStatus, "equivalence_status"), nullable=False, server_default="submitted"
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_comment: Mapped[str | None] = mapped_column(Text)

    documents: Mapped[list["EquivalenceDocument"]] = relationship(back_populates="request")


class EquivalenceDocument(IdMixin, TimestampMixin, DemoMixin, Base):
    """Pièce justificative (le fichier est stocké hors base, ici seulement ses métadonnées)."""

    __tablename__ = "equivalence_documents"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="sha256_format"),
    )

    equivalence_request_id: Mapped[int] = mapped_column(
        ForeignKey("equivalence_requests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    document_type: Mapped[EquivalenceDocumentType] = mapped_column(
        pg_enum(EquivalenceDocumentType, "equivalence_document_type"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    request: Mapped[EquivalenceRequest] = relationship(back_populates="documents")


# ----------------------------------------------------------------------------- QCM
class Qcm(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "qcm"
    __table_args__ = (
        CheckConstraint("max_score > 0", name="max_score_positive"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= max_score)", name="score_range"),
        CheckConstraint("status <> 'completed' OR (score IS NOT NULL AND completed_at IS NOT NULL)", name="completed_has_score"),
        CheckConstraint("generated_by <> 'template' OR template_code IS NOT NULL", name="template_has_code"),
    )

    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False, index=True)
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_by: Mapped[QcmGeneratedBy] = mapped_column(pg_enum(QcmGeneratedBy, "qcm_generated_by"), nullable=False)
    template_code: Mapped[str | None] = mapped_column(String(100))
    model_name: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[QcmStatus] = mapped_column(pg_enum(QcmStatus, "qcm_status"), nullable=False, server_default="generated")
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    max_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    summary_for_interviewer: Mapped[str | None] = mapped_column(Text)  # synthèse pour le responsable d'entretien
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    questions: Mapped[list["QcmQuestion"]] = relationship(back_populates="qcm", order_by="QcmQuestion.position")


class QcmQuestion(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "qcm_questions"
    __table_args__ = (
        UniqueConstraint("qcm_id", "position"),
        CheckConstraint("jsonb_typeof(choices) = 'array' AND jsonb_array_length(choices) >= 2", name="choices_array"),
        CheckConstraint(
            "correct_choice_index >= 0 AND correct_choice_index < jsonb_array_length(choices)",
            name="correct_choice_in_range",
        ),
        CheckConstraint("points > 0", name="points_positive"),
    )

    qcm_id: Mapped[int] = mapped_column(ForeignKey("qcm.id", ondelete="RESTRICT"), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(100))
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[list] = mapped_column(JSONB, nullable=False)
    correct_choice_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="1")
    explanation: Mapped[str | None] = mapped_column(Text)

    qcm: Mapped[Qcm] = relationship(back_populates="questions")


class QcmAnswer(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "qcm_answers"
    __table_args__ = (CheckConstraint("points_awarded >= 0", name="points_positive"),)

    question_id: Mapped[int] = mapped_column(
        ForeignKey("qcm_questions.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    selected_choice_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    points_awarded: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="0")
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ------------------------------------------------------------ Rendez-vous / entretiens
class Appointment(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("duration_minutes BETWEEN 5 AND 240", name="duration_range"),
        CheckConstraint("mode <> 'online' OR meeting_url IS NOT NULL", name="online_has_url"),
        CheckConstraint("status <> 'cancelled' OR cancellation_reason IS NOT NULL", name="cancel_has_reason"),
        Index("ix_appointments_organizer_scheduled", "organizer_id", "scheduled_at"),
    )

    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False, index=True)
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="30")
    mode: Mapped[AppointmentMode] = mapped_column(pg_enum(AppointmentMode, "appointment_mode"), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    meeting_url: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[AppointmentStatus] = mapped_column(
        pg_enum(AppointmentStatus, "appointment_status"), nullable=False, server_default="scheduled"
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text)


class InterviewResult(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "interview_results"
    __table_args__ = (CheckConstraint("score IS NULL OR score BETWEEN 0 AND 20", name="score_range"),)

    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    observations: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    opinion: Mapped[InterviewOpinion] = mapped_column(pg_enum(InterviewOpinion, "interview_opinion"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Decision(IdMixin, TimestampMixin, DemoMixin, Base):
    """Décision OFFICIELLE : toujours prise par un humain responsable (trigger SQL)."""

    __tablename__ = "decisions"
    __table_args__ = (
        CheckConstraint(
            "decision NOT IN ('admitted', 'admitted_with_conditions') OR program_id IS NOT NULL",
            name="admission_has_program",
        ),
        CheckConstraint(
            "decision <> 'admitted_with_conditions' OR observations IS NOT NULL", name="conditions_explained"
        ),
    )

    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"), nullable=False, index=True)
    program_id: Mapped[int | None] = mapped_column(ForeignKey("programs.id", ondelete="RESTRICT"), index=True)
    decision: Mapped[DecisionValue] = mapped_column(pg_enum(DecisionValue, "decision_value"), nullable=False)
    observations: Mapped[str | None] = mapped_column(Text)
    responsible_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------- Relances / notifications
class Notification(IdMixin, TimestampMixin, DemoMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("status <> 'sent' OR sent_at IS NOT NULL", name="sent_has_date"),
        CheckConstraint("attempts >= 0", name="attempts_positive"),
        Index("ix_notifications_status_scheduled", "status", "scheduled_for"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    dossier_id: Mapped[int | None] = mapped_column(ForeignKey("dossiers.id", ondelete="RESTRICT"), index=True)
    kind: Mapped[NotificationKind] = mapped_column(pg_enum(NotificationKind, "notification_kind"), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel"), nullable=False, server_default="email"
    )
    template_code: Mapped[str | None] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status: Mapped[NotificationStatus] = mapped_column(
        pg_enum(NotificationStatus, "notification_status"), nullable=False, server_default="pending"
    )
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------- Audit / historique
class AuditLog(Base):
    """Journal des actions (append-only : UPDATE/DELETE interdits par trigger). Aucun secret."""

    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("actor_type <> 'user' OR actor_user_id IS NOT NULL", name="user_actor_has_id"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_occurred_at", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    actor_type: Mapped[ActorType] = mapped_column(pg_enum(ActorType, "actor_type"), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # ex. "program.create"
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    details: Mapped[dict | None] = mapped_column(JSONB)
    request_id: Mapped[str | None] = mapped_column(String(64))


class StatusHistory(Base):
    """Historique des changements de statut, alimenté automatiquement par trigger."""

    __tablename__ = "status_history"
    __table_args__ = (Index("ix_status_history_entity", "entity_type", "entity_id", "changed_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    # Renseigné via SET LOCAL app.current_user_id par le backend (NULL = système).
    changed_by: Mapped[int | None] = mapped_column(BigInteger)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
