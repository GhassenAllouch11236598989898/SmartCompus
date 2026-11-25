"""SA-36 — Contexte catalogue envoyé au LLM avec chaque question.

En attendant le pipeline RAG (pgvector, autre epic), le chatbot reçoit un résumé compact de toutes
les formations **publiées** : durée, mode, conditions d'admission, frais de l'année la plus récente,
débouchés, passerelles et campagnes ouvertes, chacun avec sa source. Le catalogue DEMO tient en
~2 500 caractères. Quand le RAG sera prêt, il suffira de remplacer ``catalogue_context`` par la
recherche des passages pertinents (même signature : session -> texte).
"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AdmissionCampaign, Program, ProgramPathway
from app.models.catalog import CampaignStatus, FeeType, ProgramStatus

_MODES = {"on_site": "présentiel", "hybrid": "hybride", "online": "en ligne"}
_FEES = {FeeType.registration: "inscription", FeeType.tuition: "scolarité"}


def _money(amount: Decimal, currency: str) -> str:
    whole = f"{amount:,.3f}".rstrip("0").rstrip(".").replace(",", " ")
    return f"{whole} {currency}"


def catalogue_context(db: Session) -> str:
    programs = list(
        db.scalars(
            select(Program)
            .where(Program.status == ProgramStatus.published)
            .options(
                selectinload(Program.admission_conditions),
                selectinload(Program.prerequisites),
                selectinload(Program.career_outcomes),
                selectinload(Program.tuition_fees),
                selectinload(Program.outgoing_pathways).joinedload(ProgramPathway.to_program),
            )
            .order_by(Program.institution_id, Program.title)
        ).unique().all()
    )
    if not programs:
        return "Aucune formation publiée pour le moment."

    by_institution: dict[str, list[str]] = defaultdict(list)
    for p in programs:
        years = sorted({f.academic_year for f in p.tuition_fees}, reverse=True)
        year = years[0] if years else None
        fees = [f for f in p.tuition_fees if f.academic_year == year]
        conditions = [c for c in p.admission_conditions if c.academic_year in (year, None)] or p.admission_conditions
        parts = [
            f"- {p.title} [{p.code}] : {p.duration_semesters / 2:g} an(s) "
            f"({p.duration_semesters} semestres), {_MODES.get(p.study_mode.value, p.study_mode.value)}, "
            f"langue {p.teaching_language}.",
        ]
        if p.summary:
            parts.append(f"  Contenu : {p.summary}")
        if p.prerequisites:
            parts.append("  Prérequis : " + " ; ".join(r.label for r in p.prerequisites))
        if conditions:
            parts.append("  Admission : " + " ; ".join(
                c.description.rstrip(".")
                + (f" [moyenne minimale {c.minimum_average.normalize():f}/20]" if c.minimum_average else "")
                for c in conditions))
        if fees:
            parts.append(f"  Frais {year} : " + ", ".join(
                f"{_FEES.get(f.fee_type, f.fee_type.value)} {_money(f.amount, f.currency)}"
                + (f" [{f.payment_terms.rstrip('.')}]" if f.payment_terms else "")
                for f in sorted(fees, key=lambda f: f.fee_type.value, reverse=True)))
        if p.career_outcomes:
            parts.append("  Débouchés : " + ", ".join(o.title for o in p.career_outcomes))
        for pw in p.outgoing_pathways:
            if pw.to_program.status == ProgramStatus.published:
                parts.append(f"  Passerelle : vers {pw.to_program.title}" + (f" [{pw.conditions.rstrip('.')}]" if pw.conditions else ""))
        parts.append(f"  Source : {p.source_document.title} (version {p.source_document.version})")
        by_institution[p.institution.code].append("\n".join(parts))

    lines: list[str] = []
    for code, items in by_institution.items():
        lines.append(f"## {code}")
        lines.extend(items)

    campaigns = db.scalars(
        select(AdmissionCampaign).where(AdmissionCampaign.status == CampaignStatus.open)
        .order_by(AdmissionCampaign.closes_at)
    ).all()
    if campaigns:
        lines.append("## Campagnes d'admission ouvertes")
        lines.extend(f"- {c.name} : du {c.opens_at:%d/%m/%Y} au {c.closes_at:%d/%m/%Y}" for c in campaigns)
    return "\n".join(lines)

