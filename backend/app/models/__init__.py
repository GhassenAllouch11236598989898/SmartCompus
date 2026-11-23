"""Import de tous les modèles pour qu'ils soient enregistrés dans Base.metadata (Alembic)."""

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

__all__ = [
    "Base",
    "AdmissionCampaign",
    "AdmissionCondition",
    "CareerOutcome",
    "Institution",
    "Program",
    "ProgramPathway",
    "ProgramPrerequisite",
    "ProgramType",
    "SourceDocument",
    "TuitionFee",
]
