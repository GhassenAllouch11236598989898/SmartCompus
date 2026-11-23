"""Schémas Pydantic de l'API catalogue (SA-20 / SA-21). Champs JSON en anglais snake_case."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.catalog import (
    AdmissionConditionKind,
    FeeType,
    PrerequisiteKind,
    ProgramStatus,
    StudyMode,
)
from app.schemas.common import ORMModel, SourceRef

AcademicYear = Annotated[str, Field(pattern=r"^[0-9]{4}-[0-9]{4}$", examples=["2026-2027"])]
ProgramCode = Annotated[str, Field(pattern=r"^[A-Z0-9_-]{2,40}$", examples=["IIT-ING-GI"])]


# ------------------------------------------------------------------------- lecture
class InstitutionRef(ORMModel):
    id: int
    code: str
    name: str


class ProgramTypeRef(ORMModel):
    id: int
    code: str
    label: str


class FormationRef(ORMModel):
    id: int
    code: str
    title: str


class TracedItem(ORMModel):
    """Toute information du catalogue expose sa source et sa date de mise à jour."""

    updated_at: datetime
    source: SourceRef = Field(validation_alias="source_document")
    is_demo: bool


class PrerequisiteOut(TracedItem):
    id: int
    kind: PrerequisiteKind
    label: str
    description: str | None
    is_mandatory: bool


class CareerOutcomeOut(TracedItem):
    id: int
    title: str
    sector: str | None
    description: str | None


class PathwayOut(TracedItem):
    id: int
    to_formation: FormationRef = Field(validation_alias="to_program")
    entry_level: str | None
    conditions: str | None


class AdmissionConditionOut(TracedItem):
    id: int
    academic_year: str | None = Field(description="NULL = valable pour toutes les années")
    kind: AdmissionConditionKind
    description: str
    minimum_average: Decimal | None
    eligible_bac_sections: list[str] | None


class TuitionFeeOut(TracedItem):
    id: int
    academic_year: str
    fee_type: FeeType
    amount: Decimal = Field(description="Montant décimal sérialisé en chaîne (précision monétaire)")
    currency: str
    payment_terms: str | None


class FormationSummary(TracedItem):
    id: int
    code: str
    title: str
    summary: str | None
    institution: InstitutionRef
    program_type: ProgramTypeRef
    duration_semesters: int
    study_mode: StudyMode
    status: ProgramStatus

    @computed_field  # type: ignore[prop-decorator]
    @property
    def duration_years(self) -> float:
        return self.duration_semesters / 2


class FormationDetail(FormationSummary):
    description: str | None
    teaching_language: str
    diploma_awarded: str | None
    published_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    prerequisites: list[PrerequisiteOut]
    career_outcomes: list[CareerOutcomeOut]
    pathways: list[PathwayOut] = Field(validation_alias="outgoing_pathways")


# --------------------------------------------------------------------------- SA-21
class FeeTotal(BaseModel):
    academic_year: str
    currency: str
    total: Decimal


class TuitionFeesResponse(BaseModel):
    formation: FormationRef
    academic_year: str | None = Field(description="Filtre appliqué (NULL = toutes les années)")
    items: list[TuitionFeeOut]
    totals: list[FeeTotal]
    last_updated_at: datetime | None


class AdmissionConditionsResponse(BaseModel):
    formation: FormationRef
    academic_year: str | None
    conditions: list[AdmissionConditionOut]
    prerequisites: list[PrerequisiteOut]
    last_updated_at: datetime | None


class ComparedFormation(BaseModel):
    formation: FormationSummary
    diploma_awarded: str | None
    teaching_language: str
    fees: list[TuitionFeeOut]
    fees_total: Decimal | None
    currency: str | None
    admission_conditions: list[AdmissionConditionOut]
    prerequisites: list[PrerequisiteOut]
    career_outcomes: list[CareerOutcomeOut]
    pathways: list[PathwayOut]


class ComparisonResponse(BaseModel):
    academic_year: str | None = Field(description="Année des tarifs/conditions comparés")
    formations: list[ComparedFormation]
    last_updated_at: datetime | None


# ------------------------------------------------------------------------ écriture
class _FormationFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    institution_id: int = Field(gt=0)
    program_type_id: int = Field(gt=0)
    code: ProgramCode
    title: str = Field(min_length=3, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    duration_semesters: int = Field(ge=1, le=12)
    study_mode: StudyMode = StudyMode.on_site
    teaching_language: str = Field(default="fr", min_length=2, max_length=50)
    diploma_awarded: str | None = Field(default=None, max_length=255)
    source_document_id: int = Field(gt=0, description="Document source officiel (traçabilité obligatoire)")


class FormationCreate(_FormationFields):
    status: ProgramStatus = ProgramStatus.draft

    @model_validator(mode="after")
    def _no_archived_creation(self) -> Self:
        if self.status == ProgramStatus.archived:
            raise ValueError("une formation ne peut pas être créée archivée")
        return self


class FormationReplace(_FormationFields):
    """PUT : remplacement complet (tous les champs requis)."""

    status: ProgramStatus


class FormationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    institution_id: int | None = Field(default=None, gt=0)
    program_type_id: int | None = Field(default=None, gt=0)
    code: ProgramCode | None = None
    title: str | None = Field(default=None, min_length=3, max_length=255)
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    duration_semesters: int | None = Field(default=None, ge=1, le=12)
    study_mode: StudyMode | None = None
    teaching_language: str | None = Field(default=None, min_length=2, max_length=50)
    diploma_awarded: str | None = Field(default=None, max_length=255)
    source_document_id: int | None = Field(default=None, gt=0)
    status: ProgramStatus | None = None

    @model_validator(mode="after")
    def _not_empty(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("au moins un champ doit être fourni")
        required = {"institution_id", "program_type_id", "code", "title", "duration_semesters",
                    "study_mode", "teaching_language", "source_document_id", "status"}
        nulls = sorted(f for f in self.model_fields_set & required if getattr(self, f) is None)
        if nulls:
            raise ValueError(f"champs non annulables : {', '.join(nulls)}")
        return self
