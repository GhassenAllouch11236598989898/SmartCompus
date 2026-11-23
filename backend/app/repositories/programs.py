"""Accès aux données du catalogue (aucune règle métier ici : voir services/formations.py)."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AdmissionCondition,
    Institution,
    Program,
    ProgramPathway,
    ProgramPrerequisite,
    ProgramType,
    SourceDocument,
    TuitionFee,
)
from app.models.catalog import ProgramStatus

SORTS = {
    "titre": (Program.title.asc(), Program.id.asc()),
    "duree": (Program.duration_semesters.asc(), Program.title.asc(), Program.id.asc()),
    "recent": (Program.updated_at.desc(), Program.id.desc()),
}


@dataclass
class ProgramFilters:
    statuses: Sequence[ProgramStatus] = (ProgramStatus.published,)
    # Restriction de périmètre : None = pas de restriction, sinon établissements autorisés
    # pour les formations NON publiées.
    unpublished_institution_ids: Sequence[int] | None = None
    institution_code: str | None = None
    program_type_code: str | None = None
    duration_min: int | None = None
    duration_max: int | None = None
    search: str | None = None
    sort: str = "titre"


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtered(stmt: Select, f: ProgramFilters) -> Select:
    stmt = stmt.where(Program.status.in_(list(f.statuses)))
    if f.unpublished_institution_ids is not None:
        stmt = stmt.where(
            or_(Program.status == ProgramStatus.published, Program.institution_id.in_(list(f.unpublished_institution_ids)))
        )
    if f.institution_code:
        stmt = stmt.where(Program.institution.has(func.upper(Institution.code) == f.institution_code.upper()))
    if f.program_type_code:
        stmt = stmt.where(Program.program_type.has(func.upper(ProgramType.code) == f.program_type_code.upper()))
    if f.duration_min is not None:
        stmt = stmt.where(Program.duration_semesters >= f.duration_min)
    if f.duration_max is not None:
        stmt = stmt.where(Program.duration_semesters <= f.duration_max)
    if f.search:
        pattern = f"%{_escape_like(f.search)}%"
        stmt = stmt.where(
            or_(
                Program.search_vector.op("@@")(func.websearch_to_tsquery("french", f.search)),
                Program.title.ilike(pattern, escape="\\"),
                Program.code.ilike(pattern, escape="\\"),
            )
        )
    return stmt


def list_programs(db: Session, f: ProgramFilters, page: int, page_size: int) -> tuple[list[Program], int]:
    total = db.scalar(_filtered(select(func.count(Program.id)), f)) or 0
    stmt = _filtered(select(Program), f).order_by(*SORTS.get(f.sort, SORTS["titre"]))
    items = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(items), total


def get_program(db: Session, program_id: int, *, with_details: bool = False) -> Program | None:
    stmt = select(Program).where(Program.id == program_id)
    if with_details:
        stmt = stmt.options(
            selectinload(Program.prerequisites),
            selectinload(Program.career_outcomes),
            selectinload(Program.outgoing_pathways).joinedload(ProgramPathway.to_program),
            selectinload(Program.admission_conditions),
            selectinload(Program.tuition_fees),
        )
    return db.scalars(stmt).unique().first()


def get_programs(db: Session, ids: Sequence[int]) -> list[Program]:
    stmt = (
        select(Program)
        .where(Program.id.in_(list(ids)))
        .options(
            selectinload(Program.prerequisites),
            selectinload(Program.career_outcomes),
            selectinload(Program.outgoing_pathways).joinedload(ProgramPathway.to_program),
            selectinload(Program.admission_conditions),
            selectinload(Program.tuition_fees),
        )
    )
    return list(db.scalars(stmt).unique().all())


def code_exists(db: Session, code: str, exclude_id: int | None = None) -> bool:
    stmt = select(Program.id).where(Program.code == code)
    if exclude_id is not None:
        stmt = stmt.where(Program.id != exclude_id)
    return db.scalar(stmt) is not None


def tuition_fees(db: Session, program_id: int, academic_year: str | None) -> list[TuitionFee]:
    stmt = select(TuitionFee).where(TuitionFee.program_id == program_id)
    if academic_year:
        stmt = stmt.where(TuitionFee.academic_year == academic_year)
    stmt = stmt.order_by(TuitionFee.academic_year.desc(), TuitionFee.fee_type)
    return list(db.scalars(stmt).unique().all())


def admission_conditions(db: Session, program_id: int, academic_year: str | None) -> list[AdmissionCondition]:
    stmt = select(AdmissionCondition).where(AdmissionCondition.program_id == program_id)
    if academic_year:
        stmt = stmt.where(
            or_(AdmissionCondition.academic_year == academic_year, AdmissionCondition.academic_year.is_(None))
        )
    stmt = stmt.order_by(AdmissionCondition.academic_year.desc().nulls_last(), AdmissionCondition.position)
    return list(db.scalars(stmt).unique().all())


def prerequisites(db: Session, program_id: int) -> list[ProgramPrerequisite]:
    stmt = (
        select(ProgramPrerequisite)
        .where(ProgramPrerequisite.program_id == program_id)
        .order_by(ProgramPrerequisite.position, ProgramPrerequisite.id)
    )
    return list(db.scalars(stmt).unique().all())


def latest_fee_year(db: Session, program_ids: Sequence[int]) -> str | None:
    return db.scalar(select(func.max(TuitionFee.academic_year)).where(TuitionFee.program_id.in_(list(program_ids))))


def exists(db: Session, model: type, obj_id: int) -> bool:
    return db.get(model, obj_id) is not None


def source_document(db: Session, doc_id: int) -> SourceDocument | None:
    return db.get(SourceDocument, doc_id)
