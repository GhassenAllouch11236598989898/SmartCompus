"""Règles métier du catalogue : visibilité, périmètre RBAC, archivage, traçabilité, audit."""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, UnprocessableError
from app.models import AuditLog, Institution, Program, ProgramType, SourceDocument, User
from app.models.catalog import ProgramStatus, SourceDocumentStatus
from app.models.identity import RoleCode
from app.repositories import programs as repo
from app.schemas.formations import (
    AdmissionConditionOut,
    AdmissionConditionsResponse,
    CareerOutcomeOut,
    ComparedFormation,
    ComparisonResponse,
    FeeTotal,
    FormationCreate,
    FormationDetail,
    FormationPatch,
    FormationRef,
    FormationReplace,
    FormationSummary,
    PathwayOut,
    PrerequisiteOut,
    TuitionFeeOut,
    TuitionFeesResponse,
)

_INSTITUTION_ROLES = (RoleCode.responsable_iit, RoleCode.responsable_isb)


# ------------------------------------------------------------------- périmètre
def managed_institution_ids(user: User | None) -> list[int] | None:
    """None = tous les établissements ; [] = aucun ; sinon liste des établissements gérés."""
    if user is None:
        return []
    if RoleCode.admin in user.role_codes:
        return None
    return sorted({r.institution_id for r in user.roles if r.code in _INSTITUTION_ROLES and r.institution_id})


def readable_unpublished_ids(user: User | None) -> list[int] | None:
    """Établissements dont l'utilisateur peut voir les formations non publiées."""
    if user is not None and RoleCode.direction in user.role_codes:
        return None
    return managed_institution_ids(user)


def _can_read(user: User | None, program: Program) -> bool:
    if program.status == ProgramStatus.published:
        return True
    allowed = readable_unpublished_ids(user)
    return allowed is None or program.institution_id in allowed


def _assert_can_manage(user: User, institution_id: int) -> None:
    allowed = managed_institution_ids(user)
    if allowed is not None and institution_id not in allowed:
        raise ForbiddenError("Cette formation est hors de votre périmètre (établissement).")


def get_visible_program(db: Session, user: User | None, program_id: int, *, with_details: bool = False) -> Program:
    program = repo.get_program(db, program_id, with_details=with_details)
    if program is None or not _can_read(user, program):
        # 404 (et non 403) pour ne pas révéler l'existence d'un brouillon.
        raise NotFoundError(f"Formation {program_id} introuvable.")
    return program


# ----------------------------------------------------------------------- lecture
def list_formations(
    db: Session,
    user: User | None,
    *,
    status: ProgramStatus | None,
    page: int,
    page_size: int,
    **filters: Any,
) -> tuple[list[FormationSummary], int]:
    unpublished_scope = readable_unpublished_ids(user)
    if status is None:
        statuses = [ProgramStatus.published]
    else:
        if status != ProgramStatus.published and unpublished_scope == []:
            raise ForbiddenError("Seules les formations publiées sont consultables sans rôle de gestion.")
        statuses = [status]
    f = repo.ProgramFilters(statuses=statuses, unpublished_institution_ids=unpublished_scope, **filters)
    items, total = repo.list_programs(db, f, page, page_size)
    return [FormationSummary.model_validate(p) for p in items], total


def _visible_pathways(user: User | None, program: Program) -> list[PathwayOut]:
    return [PathwayOut.model_validate(w) for w in program.outgoing_pathways if _can_read(user, w.to_program)]


def formation_detail(db: Session, user: User | None, program_id: int) -> FormationDetail:
    program = get_visible_program(db, user, program_id, with_details=True)
    return _detail(user, program)


def _detail(user: User | None, program: Program) -> FormationDetail:
    # Les passerelles vers une formation non visible (brouillon) sont masquées.
    return FormationDetail.model_validate(program).model_copy(update={"pathways": _visible_pathways(user, program)})


def _last_updated(*groups: list) -> datetime | None:
    dates = [x.updated_at for g in groups for x in g]
    return max(dates) if dates else None


def _totals(fees: list[TuitionFeeOut]) -> list[FeeTotal]:
    sums: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for fee in fees:
        sums[(fee.academic_year, fee.currency)] += fee.amount
    return [FeeTotal(academic_year=y, currency=c, total=t) for (y, c), t in sorted(sums.items(), reverse=True)]


def formation_fees(db: Session, user: User | None, program_id: int, academic_year: str | None) -> TuitionFeesResponse:
    program = get_visible_program(db, user, program_id)
    items = [TuitionFeeOut.model_validate(x) for x in repo.tuition_fees(db, program.id, academic_year)]
    return TuitionFeesResponse(
        formation=FormationRef.model_validate(program),
        academic_year=academic_year,
        items=items,
        totals=_totals(items),
        last_updated_at=_last_updated(items),
    )


def formation_admission_conditions(
    db: Session, user: User | None, program_id: int, academic_year: str | None
) -> AdmissionConditionsResponse:
    program = get_visible_program(db, user, program_id)
    conditions = [AdmissionConditionOut.model_validate(x) for x in repo.admission_conditions(db, program.id, academic_year)]
    prereqs = [PrerequisiteOut.model_validate(x) for x in repo.prerequisites(db, program.id)]
    return AdmissionConditionsResponse(
        formation=FormationRef.model_validate(program),
        academic_year=academic_year,
        conditions=conditions,
        prerequisites=prereqs,
        last_updated_at=_last_updated(conditions, prereqs),
    )


def compare_formations(db: Session, user: User | None, ids: list[int], academic_year: str | None) -> ComparisonResponse:
    found = {p.id: p for p in repo.get_programs(db, ids) if _can_read(user, p)}
    missing = [i for i in ids if i not in found]
    if missing:
        raise NotFoundError("Formation(s) introuvable(s).", details={"missing_ids": missing})
    year = academic_year or repo.latest_fee_year(db, ids)
    compared: list[ComparedFormation] = []
    all_items: list = []
    for pid in ids:  # ordre demandé conservé
        p = found[pid]
        fees = [TuitionFeeOut.model_validate(f) for f in p.tuition_fees if year is None or f.academic_year == year]
        fees.sort(key=lambda f: f.fee_type.value)
        conds = [
            AdmissionConditionOut.model_validate(c)
            for c in p.admission_conditions
            if year is None or c.academic_year in (year, None)
        ]
        prereqs = [PrerequisiteOut.model_validate(x) for x in p.prerequisites]
        outcomes = [CareerOutcomeOut.model_validate(x) for x in p.career_outcomes]
        pathways = _visible_pathways(user, p)
        currencies = {f.currency for f in fees}
        compared.append(
            ComparedFormation(
                formation=FormationSummary.model_validate(p),
                diploma_awarded=p.diploma_awarded,
                teaching_language=p.teaching_language,
                fees=fees,
                fees_total=sum((f.amount for f in fees), Decimal("0")) if len(currencies) == 1 else None,
                currency=currencies.pop() if len(currencies) == 1 else None,
                admission_conditions=conds,
                prerequisites=prereqs,
                career_outcomes=outcomes,
                pathways=pathways,
            )
        )
        all_items += [compared[-1].formation, *fees, *conds, *prereqs, *outcomes, *pathways]
    return ComparisonResponse(academic_year=year, formations=compared, last_updated_at=_last_updated(all_items))


# ---------------------------------------------------------------------- écriture
def _set_actor(db: Session, user: User) -> None:
    # Utilisé par le trigger log_status_change (status_history.changed_by).
    db.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": str(user.id)})


def _validate_references(db: Session, data: dict[str, Any]) -> None:
    errors = []
    if "institution_id" in data and not repo.exists(db, Institution, data["institution_id"]):
        errors.append({"loc": ["body", "institution_id"], "msg": "établissement inexistant", "type": "reference"})
    if "program_type_id" in data and not repo.exists(db, ProgramType, data["program_type_id"]):
        errors.append({"loc": ["body", "program_type_id"], "msg": "type de parcours inexistant", "type": "reference"})
    if "source_document_id" in data:
        doc: SourceDocument | None = repo.source_document(db, data["source_document_id"])
        if doc is None:
            errors.append({"loc": ["body", "source_document_id"], "msg": "document source inexistant", "type": "reference"})
        elif doc.status == SourceDocumentStatus.archived:
            errors.append({"loc": ["body", "source_document_id"], "msg": "document source archivé", "type": "reference"})
    if errors:
        raise UnprocessableError("Références invalides.", details=errors)


def _apply_status_dates(program: Program, new_status: ProgramStatus | None) -> None:
    if new_status is None:
        return
    now = datetime.now(UTC)
    if new_status == ProgramStatus.published and program.published_at is None:
        program.published_at = now
    if new_status == ProgramStatus.archived:
        if program.archived_at is None:
            program.archived_at = now
    else:
        program.archived_at = None


def _audit(db: Session, user: User, action: str, program: Program, changes: dict[str, Any]) -> None:
    db.add(
        AuditLog(
            actor_type="user",
            actor_user_id=user.id,
            action=action,
            entity_type="programs",
            entity_id=program.id,
            details={"fields": sorted(changes), "code": program.code},
        )
    )


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "uq_programs_code" in str(exc.orig):
            raise ConflictError("Ce code de formation est déjà utilisé.") from None
        raise UnprocessableError("Contrainte de données violée.") from None


def create_formation(db: Session, user: User, payload: FormationCreate) -> FormationDetail:
    data = payload.model_dump()
    _assert_can_manage(user, data["institution_id"])
    _validate_references(db, data)
    if repo.code_exists(db, data["code"]):
        raise ConflictError("Ce code de formation est déjà utilisé.")
    _set_actor(db, user)
    program = Program(**data)
    _apply_status_dates(program, payload.status)
    db.add(program)
    db.flush()
    _audit(db, user, "program.create", program, data)
    _commit(db)
    return formation_detail(db, user, program.id)


def update_formation(
    db: Session, user: User, program_id: int, payload: FormationReplace | FormationPatch, *, partial: bool
) -> FormationDetail:
    program = repo.get_program(db, program_id)
    if program is None or not _can_read(user, program):
        raise NotFoundError(f"Formation {program_id} introuvable.")
    _assert_can_manage(user, program.institution_id)
    data = payload.model_dump(exclude_unset=partial)
    if "institution_id" in data:
        _assert_can_manage(user, data["institution_id"])
    _validate_references(db, data)
    if "code" in data and repo.code_exists(db, data["code"], exclude_id=program.id):
        raise ConflictError("Ce code de formation est déjà utilisé.")
    changes = {k: v for k, v in data.items() if getattr(program, k) != v}
    if changes:
        _set_actor(db, user)
        for key, value in changes.items():
            setattr(program, key, value)
        _apply_status_dates(program, changes.get("status"))
        _audit(db, user, "program.archive" if changes.get("status") == ProgramStatus.archived else "program.update",
               program, changes)
        _commit(db)
    db.expire_all()
    return formation_detail(db, user, program.id)


def archive_formation(db: Session, user: User, program_id: int) -> FormationDetail:
    return update_formation(db, user, program_id, FormationPatch(status=ProgramStatus.archived), partial=True)
