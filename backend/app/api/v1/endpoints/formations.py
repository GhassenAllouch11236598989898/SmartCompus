"""SA-20 / SA-21 — API catalogue : formations, tarifs, conditions d'admission, comparaison.

Lecture : publique (formations publiées). Écriture : admin, ou responsable de l'établissement concerné.
Pas de DELETE : une formation s'archive (PATCH status=archived ou POST /formations/{id}/archiver).
"""

import math
from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import CatalogManager, DbSession, OptionalUser
from app.core.errors import UnprocessableError
from app.models.catalog import ProgramStatus
from app.schemas.common import ERROR_RESPONSES, Page
from app.schemas.formations import (
    AdmissionConditionsResponse,
    ComparisonResponse,
    FormationCreate,
    FormationDetail,
    FormationPatch,
    FormationReplace,
    FormationSummary,
    TuitionFeesResponse,
)
from app.services import formations as service

router = APIRouter()

FormationId = Annotated[int, Path(ge=1, description="Identifiant de la formation")]
AcademicYearQuery = Annotated[
    str | None,
    Query(alias="annee_academique", pattern=r"^[0-9]{4}-[0-9]{4}$", description="ex. 2026-2027"),
]


class SortOption(str, Enum):
    titre = "titre"
    duree = "duree"
    recent = "recent"


def _responses(*codes: int) -> dict:
    return {c: ERROR_RESPONSES[c] for c in codes}


@router.get(
    "",
    response_model=Page[FormationSummary],
    summary="Lister les formations",
    description="Public : formations **publiées** uniquement. Les rôles de gestion peuvent filtrer par "
    "`statut` (brouillons/archives de leur périmètre).",
    responses=_responses(401, 403, 422),
)
def list_formations(
    db: DbSession,
    user: OptionalUser,
    etablissement: Annotated[str | None, Query(max_length=20, description="Code établissement (IIT, ISB)")] = None,
    type_parcours: Annotated[str | None, Query(max_length=30, description="LICENCE, PREPA, INGENIERIE…")] = None,
    duree_min: Annotated[int | None, Query(ge=1, le=12, description="Durée minimale (semestres)")] = None,
    duree_max: Annotated[int | None, Query(ge=1, le=12, description="Durée maximale (semestres)")] = None,
    statut: Annotated[ProgramStatus | None, Query(description="Réservé aux rôles de gestion hors 'published'")] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=100, description="Recherche plein texte")] = None,
    tri: SortOption = SortOption.titre,
    page: Annotated[int, Query(ge=1)] = 1,
    taille: Annotated[int, Query(ge=1, le=100, description="Éléments par page")] = 20,
) -> Page[FormationSummary]:
    if duree_min is not None and duree_max is not None and duree_min > duree_max:
        raise UnprocessableError(
            "duree_min doit être inférieure ou égale à duree_max.",
            details=[{"loc": ["query", "duree_min"], "msg": "duree_min > duree_max", "type": "value_error"}],
        )
    items, total = service.list_formations(
        db,
        user,
        status=statut,
        page=page,
        page_size=taille,
        institution_code=etablissement,
        program_type_code=type_parcours,
        duration_min=duree_min,
        duration_max=duree_max,
        search=q,
        sort=tri.value,
    )
    return Page(items=items, page=page, page_size=taille, total=total, pages=math.ceil(total / taille))


@router.get(
    "/comparer",
    response_model=ComparisonResponse,
    summary="Comparer 2 à 3 formations",
    description="Durée, modalités, tarifs, conditions, prérequis, débouchés et passerelles côte à côte "
    "(utilisé par l'agent d'orientation). Sans `annee_academique`, l'année de tarifs la plus récente est utilisée.",
    responses=_responses(404, 422),
)
def compare_formations(
    db: DbSession,
    user: OptionalUser,
    ids: Annotated[str, Query(description="2 à 3 identifiants séparés par des virgules, ex. 1,2,3")],
    annee_academique: AcademicYearQuery = None,
) -> ComparisonResponse:
    try:
        parsed = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        parsed = []
    if not parsed or any(i < 1 for i in parsed):
        raise UnprocessableError(
            "ids doit être une liste d'entiers positifs séparés par des virgules.",
            details=[{"loc": ["query", "ids"], "msg": "format invalide", "type": "value_error"}],
        )
    if len(set(parsed)) != len(parsed) or not 2 <= len(parsed) <= 3:
        raise UnprocessableError(
            "La comparaison porte sur 2 à 3 formations distinctes.",
            details=[{"loc": ["query", "ids"], "msg": "2 à 3 identifiants distincts", "type": "value_error"}],
        )
    return service.compare_formations(db, user, parsed, annee_academique)


@router.get(
    "/{formation_id}",
    response_model=FormationDetail,
    summary="Détail d'une formation",
    responses=_responses(404, 422),
)
def get_formation(db: DbSession, user: OptionalUser, formation_id: FormationId) -> FormationDetail:
    return service.formation_detail(db, user, formation_id)


@router.get(
    "/{formation_id}/tarifs",
    response_model=TuitionFeesResponse,
    summary="Tarifs officiels d'une formation",
    description="Chaque tarif inclut sa source documentaire et sa date de mise à jour.",
    responses=_responses(404, 422),
)
def get_tuition_fees(
    db: DbSession, user: OptionalUser, formation_id: FormationId, annee_academique: AcademicYearQuery = None
) -> TuitionFeesResponse:
    return service.formation_fees(db, user, formation_id, annee_academique)


@router.get(
    "/{formation_id}/conditions-admission",
    response_model=AdmissionConditionsResponse,
    summary="Conditions d'admission et prérequis",
    description="Avec `annee_academique`, renvoie les conditions de cette année et celles valables toutes années.",
    responses=_responses(404, 422),
)
def get_admission_conditions(
    db: DbSession, user: OptionalUser, formation_id: FormationId, annee_academique: AcademicYearQuery = None
) -> AdmissionConditionsResponse:
    return service.formation_admission_conditions(db, user, formation_id, annee_academique)


@router.post(
    "",
    response_model=FormationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une formation (admin / responsable de l'établissement)",
    responses=_responses(401, 403, 409, 422),
)
def create_formation(db: DbSession, user: CatalogManager, payload: FormationCreate) -> FormationDetail:
    return service.create_formation(db, user, payload)


@router.put(
    "/{formation_id}",
    response_model=FormationDetail,
    summary="Remplacer une formation (admin / responsable de l'établissement)",
    responses=_responses(401, 403, 404, 409, 422),
)
def replace_formation(
    db: DbSession, user: CatalogManager, formation_id: FormationId, payload: FormationReplace
) -> FormationDetail:
    return service.update_formation(db, user, formation_id, payload, partial=False)


@router.patch(
    "/{formation_id}",
    response_model=FormationDetail,
    summary="Modifier partiellement une formation (dont archivage : status=archived)",
    responses=_responses(401, 403, 404, 409, 422),
)
def patch_formation(
    db: DbSession, user: CatalogManager, formation_id: FormationId, payload: FormationPatch
) -> FormationDetail:
    return service.update_formation(db, user, formation_id, payload, partial=True)


@router.post(
    "/{formation_id}/archiver",
    response_model=FormationDetail,
    summary="Archiver une formation (aucune suppression physique)",
    responses=_responses(401, 403, 404),
)
def archive_formation(db: DbSession, user: CatalogManager, formation_id: FormationId) -> FormationDetail:
    return service.archive_formation(db, user, formation_id)
