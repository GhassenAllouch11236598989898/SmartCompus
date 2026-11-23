"""SA-13 — Périmètre de visibilité des dossiers selon le rôle.

- admin, direction : tous les dossiers ;
- responsable_iit / responsable_isb : dossiers des campagnes de leur établissement
  (roles.institution_id) ;
- responsable_entretien : dossiers ayant un rendez-vous qu'il organise ;
- candidate : uniquement ses propres dossiers ;
- tout autre cas : aucun dossier.

Les routes /responsable/* et /dossiers/me (hors SA-10) DOIVENT passer par ce filtre.
"""

from sqlalchemy import Select, exists, false, select

from app.models import AdmissionCampaign, Appointment, Candidate, Dossier, User
from app.models.identity import RoleCode

def scoped_dossiers(user: User) -> Select[tuple[Dossier]]:
    stmt = select(Dossier)
    codes = user.role_codes
    if not user.is_active:
        return stmt.where(false())
    if RoleCode.admin in codes or RoleCode.direction in codes:
        return stmt

    conditions = []
    institution_ids = [
        r.institution_id
        for r in user.roles
        if r.code in (RoleCode.responsable_iit, RoleCode.responsable_isb) and r.institution_id is not None
    ]
    if institution_ids:
        conditions.append(
            Dossier.campaign_id.in_(
                select(AdmissionCampaign.id).where(AdmissionCampaign.institution_id.in_(institution_ids))
            )
        )
    if RoleCode.responsable_entretien in codes:
        conditions.append(
            exists().where(Appointment.dossier_id == Dossier.id, Appointment.organizer_id == user.id)
        )
    if RoleCode.candidate in codes:
        conditions.append(
            Dossier.candidate_id.in_(select(Candidate.id).where(Candidate.user_id == user.id))
        )
    if not conditions:
        return stmt.where(false())

    return stmt.where(or_(*conditions))
