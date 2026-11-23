"""SA-20 — API formations : lecture publique, filtres, pagination, écriture protégée par rôle."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Institution, ProgramType, SourceDocument, StatusHistory

API = "/api/v1/formations"
PUBLISHED = {"IIT-LIC-INFO", "IIT-PREPA-MP", "IIT-ING-GI", "ISB-LIC-GEST", "ISB-MAS-MKT"}


def codes(resp) -> set[str]:
    return {f["code"] for f in resp.json()["items"]}


# ---------------------------------------------------------------------- lecture
def test_public_list_contains_only_published(client):
    r = client.get(API)
    assert r.status_code == 200
    body = r.json()
    assert codes(r) == PUBLISHED
    assert body["total"] == 5 and body["page"] == 1 and body["pages"] == 1
    item = body["items"][0]
    assert {"source", "updated_at", "institution", "program_type", "duration_years", "is_demo"} <= item.keys()
    assert item["source"]["version"] == "DEMO"


def test_pagination(client):
    r = client.get(API, params={"taille": 2, "page": 3, "tri": "titre"})
    body = r.json()
    assert (body["total"], body["pages"], body["page_size"], len(body["items"])) == (5, 3, 2, 1)
    seen = set()
    for page in (1, 2, 3):
        seen |= codes(client.get(API, params={"taille": 2, "page": page}))
    assert seen == PUBLISHED
    assert client.get(API, params={"page": 10}).json()["items"] == []


@pytest.mark.parametrize(("params", "expected"), [
    ({"etablissement": "ISB"}, {"ISB-LIC-GEST", "ISB-MAS-MKT"}),
    ({"etablissement": "iit", "type_parcours": "ingenierie"}, {"IIT-ING-GI"}),
    ({"duree_max": 4}, {"IIT-PREPA-MP", "ISB-MAS-MKT"}),
    ({"duree_min": 6, "etablissement": "IIT"}, {"IIT-LIC-INFO", "IIT-ING-GI"}),
    ({"q": "intelligence artificielle"}, {"IIT-ING-GI"}),
    ({"q": "marketing"}, {"ISB-MAS-MKT", "ISB-LIC-GEST"}),  # contenu de la licence cite le marketing
    ({"q": "e-commerce"}, {"ISB-MAS-MKT"}),
    ({"q": "100%_"}, set()),
    ({"etablissement": "INCONNU"}, set()),
])
def test_filters_and_search(client, params, expected):
    r = client.get(API, params=params)
    assert r.status_code == 200
    assert codes(r) == expected


@pytest.mark.parametrize("sort", ["titre", "duree", "recent"])
def test_sort_options(client, sort):
    assert client.get(API, params={"tri": sort}).status_code == 200


@pytest.mark.parametrize("params", [
    {"page": 0}, {"taille": 101}, {"duree_min": 0}, {"duree_min": 6, "duree_max": 2},
    {"statut": "inconnu"}, {"q": "a"}, {"tri": "prix"},
])
def test_invalid_query_returns_422(client, params):
    r = client.get(API, params=params)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_anonymous_cannot_list_drafts(client):
    r = client.get(API, params={"statut": "draft"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_managers_list_drafts_in_scope(client, auth):
    assert codes(client.get(API, params={"statut": "draft"}, headers=auth("admin"))) == {"IIT-ING-GC"}
    assert codes(client.get(API, params={"statut": "draft"}, headers=auth("responsable.iit"))) == {"IIT-ING-GC"}
    assert codes(client.get(API, params={"statut": "draft"}, headers=auth("responsable.isb"))) == set()
    assert codes(client.get(API, params={"statut": "archived"}, headers=auth("responsable.isb"))) == {"ISB-LIC-ARCH"}
    assert codes(client.get(API, params={"statut": "draft"}, headers=auth("direction"))) == {"IIT-ING-GC"}


def test_candidate_cannot_list_drafts(client, auth):
    assert client.get(API, params={"statut": "draft"}, headers=auth("amine.candidat")).status_code == 403


def test_detail(client, program_id):
    r = client.get(f"{API}/{program_id('IIT-ING-GI')}")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "IIT-ING-GI" and body["duration_years"] == 3
    assert body["prerequisites"] and body["career_outcomes"]
    assert all({"source", "updated_at"} <= x.keys() for x in body["prerequisites"] + body["career_outcomes"])


def test_detail_pathways(client, program_id):
    body = client.get(f"{API}/{program_id('IIT-PREPA-MP')}").json()
    assert [p["to_formation"]["code"] for p in body["pathways"]] == ["IIT-ING-GI"]


def test_draft_detail_is_hidden_from_public_but_visible_in_scope(client, auth, program_id):
    pid = program_id("IIT-ING-GC")
    assert client.get(f"{API}/{pid}").status_code == 404
    assert client.get(f"{API}/{pid}", headers=auth("responsable.isb")).status_code == 404
    assert client.get(f"{API}/{pid}", headers=auth("responsable.iit")).status_code == 200


def test_detail_errors(client):
    r = client.get(f"{API}/999999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    assert client.get(f"{API}/0").status_code == 422
    assert client.get(f"{API}/abc").status_code == 422


# --------------------------------------------------------------------- écriture
@pytest.fixture
def refs(db: Session) -> dict[str, int]:
    def one(model, **kw):
        return db.scalars(select(model.id).filter_by(**kw)).one()

    return {
        "iit": one(Institution, code="IIT"),
        "isb": one(Institution, code="ISB"),
        "ing": one(ProgramType, code="INGENIERIE"),
        "src_iit": one(SourceDocument, title="Brochure IIT 2026-2027 (DEMO)"),
    }


@pytest.fixture
def new_formation(refs) -> dict:
    return {
        "institution_id": refs["iit"],
        "program_type_id": refs["ing"],
        "code": "IIT-ING-TEST",
        "title": "Cycle ingénieur de test",
        "summary": "Formation créée par les tests.",
        "duration_semesters": 6,
        "study_mode": "hybrid",
        "source_document_id": refs["src_iit"],
    }


def test_write_requires_authentication(client, new_formation):
    r = client.post(API, json=new_formation)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"
    assert client.post(API, json=new_formation, headers={"Authorization": "Bearer faux.jeton"}).status_code == 401


@pytest.mark.parametrize("local", ["amine.candidat", "direction", "responsable.entretien"])
def test_write_forbidden_for_other_roles(client, auth, new_formation, local):
    r = client.post(API, json=new_formation, headers=auth(local))
    assert r.status_code == 403


def test_responsable_out_of_scope_is_forbidden(client, auth, new_formation):
    assert client.post(API, json=new_formation, headers=auth("responsable.isb")).status_code == 403


@pytest.mark.parametrize("local", ["responsable.iit", "admin"])
def test_create_formation(client, auth, db, new_formation, local):
    r = client.post(API, json=new_formation, headers=auth(local))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "draft" and body["published_at"] is None and body["source"]["id"]
    audit = db.scalars(select(AuditLog).where(AuditLog.action == "program.create", AuditLog.entity_id == body["id"])).one()
    assert audit.details["code"] == "IIT-ING-TEST"


def test_create_published_sets_publication_date(client, auth, new_formation):
    r = client.post(API, json={**new_formation, "status": "published"}, headers=auth("admin"))
    assert r.status_code == 201 and r.json()["published_at"]
    assert "IIT-ING-TEST" in codes(client.get(API, params={"taille": 100}))


def test_create_duplicate_code_conflict(client, auth, new_formation):
    r = client.post(API, json={**new_formation, "code": "IIT-ING-GI"}, headers=auth("admin"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize("override", [
    {"code": "minuscules"},
    {"duration_semesters": 0},
    {"status": "archived"},
    {"title": ""},
    {"champ_inconnu": 1},
    {"source_document_id": None},
])
def test_create_invalid_payload(client, auth, new_formation, override):
    r = client.post(API, json={**new_formation, **override}, headers=auth("admin"))
    assert r.status_code == 422


@pytest.mark.parametrize("field", ["institution_id", "program_type_id", "source_document_id"])
def test_create_invalid_reference(client, auth, new_formation, field):
    r = client.post(API, json={**new_formation, field: 999999}, headers=auth("admin"))
    assert r.status_code in (403, 422)  # établissement inconnu = hors périmètre pour un responsable
    if r.status_code == 422:
        assert r.json()["error"]["details"][0]["loc"] == ["body", field]


def test_put_replaces_formation(client, auth, program_id, refs):
    pid = program_id("IIT-LIC-INFO")
    current = client.get(f"{API}/{pid}").json()
    payload = {
        "institution_id": refs["iit"], "program_type_id": current["program_type"]["id"], "code": "IIT-LIC-INFO",
        "title": "Licence en Informatique (DEMO, modifiée)", "duration_semesters": 6, "study_mode": "on_site",
        "teaching_language": "fr", "source_document_id": current["source"]["id"], "status": "published",
    }
    r = client.put(f"{API}/{pid}", json=payload, headers=auth("responsable.iit"))
    assert r.status_code == 200 and r.json()["title"].endswith("modifiée)")
    assert r.json()["summary"] is None  # PUT = remplacement complet
    r = client.put(f"{API}/{pid}", json={"title": "incomplet"}, headers=auth("admin"))
    assert r.status_code == 422


def test_patch_and_archive_instead_of_delete(client, auth, db, program_id):
    pid = program_id("IIT-LIC-INFO")
    r = client.patch(f"{API}/{pid}", json={"summary": "Résumé modifié"}, headers=auth("responsable.iit"))
    assert r.status_code == 200 and r.json()["summary"] == "Résumé modifié"

    r = client.patch(f"{API}/{pid}", json={"status": "archived"}, headers=auth("responsable.iit"))
    assert r.status_code == 200
    assert r.json()["status"] == "archived" and r.json()["archived_at"]
    assert client.get(f"{API}/{pid}").status_code == 404  # plus visible publiquement
    history = db.scalars(select(StatusHistory).where(
        StatusHistory.entity_type == "programs", StatusHistory.entity_id == pid
    ).order_by(StatusHistory.id.desc())).first()
    assert (history.old_status, history.new_status) == ("published", "archived")
    assert history.changed_by == db.scalars(select(AuditLog.actor_user_id).where(
        AuditLog.action == "program.archive", AuditLog.entity_id == pid)).one()

    r = client.patch(f"{API}/{pid}", json={"status": "published"}, headers=auth("admin"))
    assert r.json()["archived_at"] is None


def test_archive_endpoint_and_delete_not_allowed(client, auth, program_id):
    pid = program_id("ISB-MAS-MKT")
    assert client.delete(f"{API}/{pid}", headers=auth("admin")).status_code == 405
    r = client.post(f"{API}/{pid}/archiver", headers=auth("responsable.isb"))
    assert r.status_code == 200 and r.json()["status"] == "archived"
    # Ré-archiver est sans effet (idempotent).
    assert client.post(f"{API}/{pid}/archiver", headers=auth("responsable.isb")).status_code == 200


def test_patch_scope_rules(client, auth, program_id, refs):
    isb_pid, iit_pid = program_id("ISB-LIC-GEST"), program_id("IIT-ING-GI")
    assert client.patch(f"{API}/{isb_pid}", json={"title": "Piratage"}, headers=auth("responsable.iit")).status_code == 403
    r = client.patch(f"{API}/{iit_pid}", json={"institution_id": refs["isb"]}, headers=auth("responsable.iit"))
    assert r.status_code == 403  # ne peut pas transférer hors de son périmètre
    assert client.patch(f"{API}/999999", json={"title": "Inconnu"}, headers=auth("admin")).status_code == 404


@pytest.mark.parametrize("payload", [{}, {"status": None}, {"code": "IIT-ING-GI"}])
def test_patch_invalid(client, auth, program_id, payload):
    r = client.patch(f"{API}/{program_id('IIT-LIC-INFO')}", json=payload, headers=auth("admin"))
    assert r.status_code in (409, 422)


def test_expired_token_rejected(client, user_by_email, new_formation):
    from app.core.security import create_access_token

    token = create_access_token(user_by_email("admin").id, ["admin"], expires_minutes=-1)
    r = client.post(API, json=new_formation, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_deactivated_user_rejected(client, db, user_by_email, auth, new_formation):
    headers = auth("admin")
    user_by_email("admin").is_active = False
    db.flush()
    assert client.post(API, json=new_formation, headers=headers).status_code == 401
