"""SA-13 / SA-17 — règles métier garanties par la base (triggers, CHECK, privilèges)."""

from datetime import UTC, datetime

import pytest
from psycopg import errors as pg
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.models import AuditLog, Candidate, Decision, Dossier, Role, StatusHistory, User, UserRole
from app.models.identity import RoleCode


def _dossier(db: Session, local: str) -> Dossier:
    return db.scalars(
        select(Dossier).join(Candidate).join(User).where(User.email == f"{local}@demo.smartcampus.invalid")
    ).first()


def test_app_role_cannot_delete(db: Session):
    with pytest.raises(ProgrammingError) as exc:
        db.execute(text("DELETE FROM dossiers WHERE id = (SELECT min(id) FROM dossiers)"))
    assert isinstance(exc.value.orig, pg.InsufficientPrivilege)


def test_app_role_cannot_run_ddl(db: Session):
    with pytest.raises(ProgrammingError) as exc:
        db.execute(text("CREATE TABLE hack (id int)"))
    assert isinstance(exc.value.orig, pg.InsufficientPrivilege)


def test_trigger_blocks_physical_delete_even_for_owner(owner_db: Session):
    with pytest.raises(DBAPIError) as exc:
        owner_db.execute(text("DELETE FROM programs WHERE code = 'ISB-LIC-ARCH'"))
    assert isinstance(exc.value.orig, pg.RestrictViolation)


def test_audit_log_is_append_only(db: Session):
    entry = db.scalars(select(AuditLog)).first()
    with pytest.raises(DBAPIError) as exc:
        db.execute(text("UPDATE audit_log SET action = 'x' WHERE id = :id"), {"id": entry.id})
    assert isinstance(exc.value.orig, pg.RestrictViolation)


def test_status_change_is_historised_with_actor(db: Session, user_by_email):
    dossier = _dossier(db, "salma.candidat")
    actor = user_by_email("responsable.iit")
    db.execute(text("SELECT set_config('app.current_user_id', :u, true)"), {"u": str(actor.id)})
    dossier.status = "in_progress"
    db.flush()
    last = db.scalars(
        select(StatusHistory)
        .where(StatusHistory.entity_type == "dossiers", StatusHistory.entity_id == dossier.id)
        .order_by(StatusHistory.id.desc())
    ).first()
    assert (last.old_status, last.new_status, last.changed_by) == ("open", "in_progress", actor.id)


def test_updated_at_trigger(db: Session):
    dossier = _dossier(db, "salma.candidat")
    before = dossier.updated_at
    db.execute(text("UPDATE dossiers SET ai_summary = 'x', ai_summary_updated_at = now() WHERE id = :i"), {"i": dossier.id})
    db.expire_all()
    assert db.get(Dossier, dossier.id).updated_at >= before


@pytest.mark.parametrize("local", ["amine.candidat", "direction", "admin"])
def test_decision_requires_human_responsable(db: Session, user_by_email, local):
    dossier = _dossier(db, "yasmine.candidat")
    db.add(Decision(dossier_id=dossier.id, decision="rejected", responsible_id=user_by_email(local).id))
    with pytest.raises(DBAPIError) as exc:
        db.flush()
    assert isinstance(exc.value.orig, pg.CheckViolation)


def test_ai_service_account_can_never_decide(db: Session):
    role = db.scalars(select(Role).where(Role.code == RoleCode.responsable_iit)).one()
    bot = User(email="agent-ia@demo.smartcampus.invalid", full_name="Agent IA", is_service_account=True, is_demo=True)
    db.add(bot)
    db.flush()
    db.add(UserRole(user_id=bot.id, role_id=role.id))
    db.flush()
    db.add(Decision(dossier_id=_dossier(db, "yasmine.candidat").id, decision="rejected", responsible_id=bot.id))
    with pytest.raises(DBAPIError) as exc:
        db.flush()
    assert isinstance(exc.value.orig, pg.CheckViolation)


def test_responsable_can_decide(db: Session, user_by_email):
    d = Decision(dossier_id=_dossier(db, "yasmine.candidat").id, decision="waitlisted",
                 responsible_id=user_by_email("responsable.iit").id, decided_at=datetime.now(UTC))
    db.add(d)
    db.flush()
    assert d.id is not None


def test_only_one_active_dossier_per_candidate_and_campaign(db: Session):
    existing = _dossier(db, "yasmine.candidat")
    db.add(Dossier(candidate_id=existing.candidate_id, campaign_id=existing.campaign_id))
    with pytest.raises(IntegrityError):
        db.flush()


def test_plain_text_password_is_rejected(db: Session):
    db.add(User(email="clair@demo.smartcampus.invalid", full_name="X", password_hash="motdepasse"))
    with pytest.raises(IntegrityError) as exc:
        db.flush()
    assert "ck_users_password_hashed" in str(exc.value)


def test_recommendation_review_requires_reviewer(db: Session):
    with pytest.raises(IntegrityError) as exc:
        db.execute(text("UPDATE recommendations SET review_status = 'confirmed' WHERE review_status = 'pending'"))
    assert "ck_recommendations_review_consistency" in str(exc.value)


def test_catalog_requires_source_document(db: Session):
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE tuition_fees SET source_document_id = NULL"))
