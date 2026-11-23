"""Import de tous les modèles pour qu'ils soient enregistrés dans Base.metadata (Alembic)."""

from app.models.applications import (
    Appointment,
    AuditLog,
    Candidate,
    CandidateProfile,
    Consent,
    Conversation,
    Decision,
    Dossier,
    EquivalenceDocument,
    EquivalenceRequest,
    InterviewResult,
    Message,
    Notification,
    Preinscription,
    Qcm,
    QcmAnswer,
    QcmQuestion,
    Recommendation,
    StatusHistory,
)
from app.models.base import Base
from app.models.catalog import (
    AdmissionCampaign,
    AdmissionCondition,
    CareerOutcome,
    Institution,
    Program,
    ProgramPathway,
    ProgramPrerequisite,
    ProgramType,
    SourceDocument,
    TuitionFee,
)
from app.models.identity import Role, User, UserRole

__all__ = [name for name in dir() if not name.startswith("_")]
