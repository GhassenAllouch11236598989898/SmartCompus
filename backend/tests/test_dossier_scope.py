"""SA-13 — un responsable ne voit que les dossiers de son périmètre."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AdmissionCampaign, Dossier, Institution
from app.repositories.dossier_scope import scoped_dossiers


def _institutions_of(db: Session, user) -> set[str]:
    stmt = scoped_dossiers(user).subquery()
    return set(db.scalars(
        select(Institution.code)
        .join(AdmissionCampaign, AdmissionCampaign.institution_id == Institution.id)
        .join(stmt, stmt.c.campaign_id == AdmissionCampaign.id)
    ))


def _count(db: Session, user) -> int:
    return db.scalar(select(func.count()).select_from(scoped_dossiers(user).subquery()))


def test_admin_and_direction_see_everything(db: Session, user_by_email):
    total = db.scalar(select(func.count()).select_from(Dossier))
    assert _count(db, user_by_email("admin")) == total
    assert _count(db, user_by_email("direction")) == total


def test_responsable_iit_sees_only_iit(db: Session, user_by_email):
    assert _institutions_of(db, user_by_email("responsable.iit")) == {"IIT"}


def test_responsable_isb_sees_only_isb(db: Session, user_by_email):
    assert _institutions_of(db, user_by_email("responsable.isb")) == {"ISB"}
    assert _count(db, user_by_email("responsable.isb")) == 1


def test_responsable_entretien_sees_dossiers_with_his_appointments(db: Session, user_by_email):
    assert _count(db, user_by_email("responsable.entretien")) == 2  # dossiers d'Amine et Yasmine


def test_candidate_sees_only_own_dossier(db: Session, user_by_email):
    user = user_by_email("karim.candidat")
    rows = db.scalars(scoped_dossiers(user)).all()
    assert len(rows) == 1 and rows[0].candidate.user_id == user.id


def test_inactive_user_sees_nothing(db: Session, user_by_email):
    user = user_by_email("admin")
    user.is_active = False
    assert _count(db, user) == 0
