"""SA-18 — Données de démonstration (TOUTES FICTIVES, is_demo = true, sources version "DEMO").

Idempotent : chaque entité est retrouvée par sa clé naturelle puis mise à jour uniquement si
une valeur change ; relancer le script ne crée aucun doublon.

    python -m seeds.seed            # base cible : MIGRATION_DATABASE_URL (rôle owner)

Voir SEED_DATA_NOTES.md : liste des données à remplacer par les informations officielles IIT/ISB.
"""

import hashlib
import math
import random
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, hash_token
from app.models import (
    AdmissionCampaign,
    AdmissionCondition,
    Appointment,
    AuditLog,
    Candidate,
    CandidateProfile,
    CareerOutcome,
    Consent,
    Conversation,
    Decision,
    DocumentChunk,
    Dossier,
    EquivalenceDocument,
    EquivalenceRequest,
    Institution,
    InterviewResult,
    Message,
    Notification,
    Preinscription,
    Program,
    ProgramPathway,
    ProgramPrerequisite,
    ProgramType,
    Qcm,
    QcmAnswer,
    QcmQuestion,
    Recommendation,
    Role,
    SourceDocument,
    SyncJob,
    SyncLog,
    TuitionFee,
    User,
    UserRole,
)
from app.models.documents import EMBEDDING_DIM
from app.models.identity import RoleCode

T = TypeVar("T")

DEMO_VERSION = "DEMO"
DEMO_PASSWORD = "Demo2026!"  # uniquement pour les comptes de démonstration
DEMO_EMAIL_DOMAIN = "demo.smartcampus.invalid"  # TLD .invalid réservé : aucun email réel
YEAR = "2026-2027"
PREV_YEAR = "2025-2026"


def dt(y: int, m: int, d: int, h: int = 9, mi: int = 0) -> datetime:
    return datetime(y, m, d, h, mi, tzinfo=UTC)


def upsert(session: Session, model: type[T], lookup: dict[str, Any], **values: Any) -> T:
    """Retrouve par `lookup` ; crée si absent ; sinon met à jour les seuls champs différents."""
    obj = session.scalars(select(model).filter_by(**lookup)).first()
    if obj is None:
        obj = model(**lookup, **values)
        session.add(obj)
    else:
        for key, value in values.items():
            current = getattr(obj, key)
            if key == "embedding":  # vecteur numpy float32 : on ne recalcule pas un embedding existant
                if current is None:
                    setattr(obj, key, value)
            elif current != value:
                setattr(obj, key, value)
    session.flush()
    return obj


def fake_embedding(seed_text: str) -> list[float]:
    """Vecteur déterministe normalisé — FICTIF (à recalculer par le pipeline RAG)."""
    rng = random.Random(hashlib.sha256(seed_text.encode()).hexdigest())
    vec = [rng.uniform(-1, 1) for _ in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(v * v for v in vec))
    return [round(v / norm, 6) for v in vec]


def demo_hash(*parts: str) -> str:
    return hashlib.sha256("::".join(("DEMO", *parts)).encode()).hexdigest()


# =============================================================================== Catalogue
def seed_catalog(s: Session) -> dict[str, Any]:
    iit = upsert(
        s, Institution, {"code": "IIT"},
        name="IIT — nom officiel à confirmer (DEMO)",
        description="Établissement IIT (UNAP). Description FICTIVE à remplacer par la présentation officielle.",
        website=None, is_demo=True,
    )
    isb = upsert(
        s, Institution, {"code": "ISB"},
        name="ISB — nom officiel à confirmer (DEMO)",
        description="Établissement ISB. Description FICTIVE à remplacer par la présentation officielle.",
        website=None, is_demo=True,
    )
    types = {
        code: upsert(s, ProgramType, {"code": code}, label=label, is_demo=True)
        for code, label in [
            ("LICENCE", "Licence"),
            ("PREPA", "Cycle préparatoire"),
            ("INGENIERIE", "Cycle ingénieur"),
            ("MASTER", "Master"),
        ]
    }

    def source(key: str, title: str, doc_type: str, inst: Institution | None) -> SourceDocument:
        return upsert(
            s, SourceDocument, {"title": title, "version": DEMO_VERSION},
            doc_type=doc_type, institution_id=inst.id if inst else None,
            content_hash=demo_hash(key), status="active", uri=f"demo://{key}.pdf",
            language="fr", document_date=date(2026, 9, 1), last_synced_at=dt(2026, 10, 1), is_demo=True,
        )

    src = {
        "iit_brochure": source("iit_brochure", "Brochure IIT 2026-2027 (DEMO)", "brochure", iit),
        "iit_ing": source("iit_programme_ing", "Programme cycle ingénieur Génie Informatique (DEMO)", "programme", iit),
        "iit_faq": source("iit_faq", "FAQ admissions IIT (DEMO)", "faq", iit),
        "equiv": source("procedure_equivalence", "Procédure de demande d'équivalence (DEMO)", "procedure", None),
        "isb_brochure": source("isb_brochure", "Brochure ISB 2026-2027 (DEMO)", "brochure", isb),
    }

    def program(code: str, inst: Institution, ptype: str, title: str, sem: int, status: str, srcdoc: str,
                summary: str, description: str, diploma: str | None, mode: str = "on_site") -> Program:
        return upsert(
            s, Program, {"code": code},
            institution_id=inst.id, program_type_id=types[ptype].id, title=title, summary=summary,
            description=description, duration_semesters=sem, study_mode=mode, teaching_language="fr",
            diploma_awarded=diploma, status=status,
            published_at=dt(2026, 9, 15) if status == "published" else None,
            archived_at=dt(2026, 10, 1) if status == "archived" else None,
            source_document_id=src[srcdoc].id, is_demo=True,
        )

    p = {
        "lic": program(
            "IIT-LIC-INFO", iit, "LICENCE", "Licence en Informatique (DEMO)", 6, "published", "iit_brochure",
            "Licence en 3 ans : programmation, bases de données, réseaux et développement web.",
            "Contenu FICTIF : algorithmique, programmation orientée objet, bases de données, réseaux, "
            "développement web et mobile, projet de fin d'études.",
            "Licence en Informatique (intitulé à confirmer)",
        ),
        "prepa": program(
            "IIT-PREPA-MP", iit, "PREPA", "Cycle préparatoire intégré (DEMO)", 4, "published", "iit_brochure",
            "Deux ans de mathématiques, physique et informatique pour préparer le cycle ingénieur.",
            "Contenu FICTIF : analyse, algèbre, physique, initiation à la programmation, langues.",
            None,
        ),
        "ing": program(
            "IIT-ING-GI", iit, "INGENIERIE", "Cycle ingénieur Génie Informatique (DEMO)", 6, "published", "iit_ing",
            "Trois ans de formation d'ingénieur : génie logiciel, IA, cloud et systèmes.",
            "Contenu FICTIF : génie logiciel, intelligence artificielle, data science, cloud, sécurité, "
            "stages en entreprise et projet de fin d'études.",
            "Diplôme national d'ingénieur (intitulé à confirmer)",
        ),
        "draft": program(
            "IIT-ING-GC", iit, "INGENIERIE", "Cycle ingénieur Génie Civil — brouillon (DEMO)", 6, "draft", "iit_brochure",
            "Formation en préparation (non publiée).", "Brouillon FICTIF non visible du public.", None,
        ),
        "isb_lic": program(
            "ISB-LIC-GEST", isb, "LICENCE", "Licence en Gestion (DEMO)", 6, "published", "isb_brochure",
            "Licence en 3 ans : comptabilité, finance, marketing et management.",
            "Contenu FICTIF : comptabilité, finance d'entreprise, marketing, management, droit des affaires.",
            "Licence en Gestion (intitulé à confirmer)",
        ),
        "isb_mas": program(
            "ISB-MAS-MKT", isb, "MASTER", "Master Marketing digital (DEMO)", 4, "published", "isb_brochure",
            "Master en 2 ans : stratégie digitale, data marketing et e-commerce.",
            "Contenu FICTIF : marketing digital, analyse de données clients, e-commerce, communication.",
            "Master (intitulé à confirmer)", "hybrid",
        ),
        "isb_old": program(
            "ISB-LIC-ARCH", isb, "LICENCE", "Ancienne licence archivée (DEMO)", 6, "archived", "isb_brochure",
            "Formation archivée (exemple d'archivage au lieu de suppression).", "Archivée — FICTIF.", None,
        ),
    }

    prereqs = {
        "lic": [("diploma", "Baccalauréat (toutes sections scientifiques)", "Sections : Maths, Sciences exp., Informatique, Technique.")],
        "prepa": [("diploma", "Baccalauréat Mathématiques ou Sciences expérimentales", None),
                  ("subject", "Bon niveau en mathématiques", "Recommandé : moyenne en maths ≥ 12 (FICTIF).")],
        "ing": [("level", "Bac+2 scientifique validé", "Cycle préparatoire, licence (L2) ou équivalent."),
                ("subject", "Bases de programmation", None)],
        "isb_lic": [("diploma", "Baccalauréat (toutes sections)", None)],
        "isb_mas": [("level", "Licence (Bac+3) en gestion, commerce ou équivalent", None)],
    }
    for key, items in prereqs.items():
        for i, (kind, label, desc) in enumerate(items):
            upsert(s, ProgramPrerequisite, {"program_id": p[key].id, "label": label},
                   kind=kind, description=desc, is_mandatory=True, position=i,
                   source_document_id=p[key].source_document_id, is_demo=True)

    conditions = {
        "lic": [("dossier_review", "Étude du dossier scolaire (FICTIF).", Decimal("10.00"), ["Mathématiques", "Sciences expérimentales", "Informatique", "Technique"]),
                ("qcm", "QCM de positionnement en ligne (FICTIF).", None, None)],
        "prepa": [("minimum_average", "Moyenne au baccalauréat ≥ 12/20 (FICTIF).", Decimal("12.00"), ["Mathématiques", "Sciences expérimentales"]),
                  ("interview", "Entretien de motivation (FICTIF).", None, None)],
        "ing": [("dossier_review", "Étude du dossier Bac+2 (FICTIF).", Decimal("11.00"), None),
                ("qcm", "QCM ciblé : algorithmique et mathématiques (FICTIF).", None, None),
                ("interview", "Entretien avec le responsable pédagogique (FICTIF).", None, None),
                ("equivalence", "Demande d'équivalence pour les candidats hors IIT (FICTIF).", None, None)],
        "isb_lic": [("dossier_review", "Étude du dossier (FICTIF).", Decimal("10.00"), None)],
        "isb_mas": [("dossier_review", "Étude du dossier Bac+3 (FICTIF).", Decimal("11.00"), None),
                    ("interview", "Entretien de motivation (FICTIF).", None, None)],
    }
    for key, items in conditions.items():
        for i, (kind, desc, avg, sections) in enumerate(items):
            upsert(s, AdmissionCondition, {"program_id": p[key].id, "academic_year": YEAR, "position": i},
                   kind=kind, description=desc, minimum_average=avg, eligible_bac_sections=sections,
                   source_document_id=p[key].source_document_id, is_demo=True)

    outcomes = {
        "lic": [("Développeur web et mobile", "Numérique"), ("Administrateur bases de données", "Numérique")],
        "prepa": [("Poursuite en cycle ingénieur", "Études")],
        "ing": [("Ingénieur logiciel", "Numérique"), ("Data scientist / ingénieur IA", "Numérique"),
                ("Ingénieur cloud & DevOps", "Numérique")],
        "isb_lic": [("Assistant comptable", "Finance"), ("Chargé de clientèle", "Commerce")],
        "isb_mas": [("Responsable marketing digital", "Marketing"), ("Chef de projet e-commerce", "Commerce")],
    }
    for key, items in outcomes.items():
        for title, sector in items:
            upsert(s, CareerOutcome, {"program_id": p[key].id, "title": title},
                   sector=sector, description=None, source_document_id=p[key].source_document_id, is_demo=True)

    for frm, to, level, cond in [
        ("prepa", "ing", "Entrée en 1ère année du cycle ingénieur", "Validation des deux années du cycle préparatoire (FICTIF)."),
        ("lic", "ing", "Entrée en 1ère année du cycle ingénieur", "Après L2/L3 avec étude du dossier et QCM (FICTIF)."),
        ("isb_lic", "isb_mas", "Entrée en 1ère année de master", "Licence validée (FICTIF)."),
    ]:
        upsert(s, ProgramPathway, {"from_program_id": p[frm].id, "to_program_id": p[to].id},
               entry_level=level, conditions=cond, source_document_id=p[frm].source_document_id, is_demo=True)

    fees = {  # (inscription, scolarité) — MONTANTS FICTIFS
        "lic": ("300.000", "5900.000"),
        "prepa": ("300.000", "6200.000"),
        "ing": ("300.000", "7500.000"),
        "isb_lic": ("250.000", "5200.000"),
        "isb_mas": ("250.000", "6800.000"),
    }
    for key, (reg, tuition) in fees.items():
        for year, factor in [(YEAR, Decimal("1")), (PREV_YEAR, Decimal("0.95"))]:
            upsert(s, TuitionFee, {"program_id": p[key].id, "academic_year": year, "fee_type": "registration"},
                   amount=Decimal(reg), currency="TND", payment_terms="Payable à l'inscription (FICTIF).",
                   source_document_id=p[key].source_document_id, is_demo=True)
            upsert(s, TuitionFee, {"program_id": p[key].id, "academic_year": year, "fee_type": "tuition"},
                   amount=(Decimal(tuition) * factor).quantize(Decimal("0.001")), currency="TND",
                   payment_terms="Paiement en 1 ou 3 tranches (FICTIF).",
                   source_document_id=p[key].source_document_id, is_demo=True)

    camp = {
        "iit": upsert(s, AdmissionCampaign, {"institution_id": iit.id, "academic_year": YEAR, "name": "Admissions IIT 2026-2027 (DEMO)"},
                      opens_at=dt(2026, 6, 1), closes_at=dt(2026, 12, 31, 23, 59), status="open",
                      source_document_id=src["iit_brochure"].id, is_demo=True),
        "isb": upsert(s, AdmissionCampaign, {"institution_id": isb.id, "academic_year": YEAR, "name": "Admissions ISB 2026-2027 (DEMO)"},
                      opens_at=dt(2026, 6, 1), closes_at=dt(2026, 12, 31, 23, 59), status="open",
                      source_document_id=src["isb_brochure"].id, is_demo=True),
    }
    return {"iit": iit, "isb": isb, "programs": p, "sources": src, "campaigns": camp}


# ============================================================================ Utilisateurs
def seed_users(s: Session, cat: dict[str, Any]) -> dict[str, User]:
    role_defs = [
        (RoleCode.candidate, "Candidat", None),
        (RoleCode.responsable_iit, "Responsable IIT", cat["iit"].id),
        (RoleCode.responsable_isb, "Responsable ISB", cat["isb"].id),
        (RoleCode.responsable_entretien, "Responsable entretien", None),
        (RoleCode.direction, "Direction", None),
        (RoleCode.admin, "Administrateur", None),
    ]
    roles = {code: upsert(s, Role, {"code": code}, label=label, institution_id=inst) for code, label, inst in role_defs}

    def user(local: str, full_name: str, role: RoleCode) -> User:
        email = f"{local}@{DEMO_EMAIL_DOMAIN}"
        u = s.scalars(select(User).filter_by(email=email)).first()
        if u is None:  # le mot de passe n'est haché qu'à la création (bcrypt est salé)
            u = User(email=email, password_hash=hash_password(DEMO_PASSWORD), full_name=full_name, is_demo=True)
            s.add(u)
            s.flush()
        upsert(s, UserRole, {"user_id": u.id, "role_id": roles[role].id})
        return u

    users = {
        "admin": user("admin", "Admin Démo", RoleCode.admin),
        "direction": user("direction", "Direction Démo", RoleCode.direction),
        "resp_iit": user("responsable.iit", "Responsable IIT Démo", RoleCode.responsable_iit),
        "resp_isb": user("responsable.isb", "Responsable ISB Démo", RoleCode.responsable_isb),
        "resp_entretien": user("responsable.entretien", "Responsable Entretien Démo", RoleCode.responsable_entretien),
        "c1": user("amine.candidat", "Amine Démo", RoleCode.candidate),
        "c2": user("yasmine.candidat", "Yasmine Démo", RoleCode.candidate),
        "c3": user("karim.candidat", "Karim Démo", RoleCode.candidate),
        "c4": user("salma.candidat", "Salma Démo", RoleCode.candidate),
        "c5": user("oussama.candidat", "Oussama Démo", RoleCode.candidate),
    }
    s.expire_all()  # recharge user.roles
    return users


# ============================================================================ Candidatures
def seed_candidates(s: Session, cat: dict[str, Any], users: dict[str, User]) -> None:
    p, camp = cat["programs"], cat["campaigns"]
    profiles = {
        "c1": dict(first="Amine", last="Démo", birth=2008, gov="Sfax",
                   level="bac", section="Mathématiques", bac_year=2026, avg=Decimal("15.20"),
                   interests=["intelligence artificielle", "robotique"], subjects=["mathématiques", "physique"],
                   goals="Devenir ingénieur en IA.", constraints="Préférence pour Sfax.", lang="fr"),
        "c2": dict(first="Yasmine", last="Démo", birth=2008, gov="Sousse",
                   level="bac", section="Informatique", bac_year=2026, avg=Decimal("13.40"),
                   interests=["développement web", "design"], subjects=["informatique", "anglais"],
                   goals="Travailler rapidement comme développeuse.", constraints="Budget limité.", lang="tn_darija"),
        "c3": dict(first="Karim", last="Démo", birth=2005, gov="Tunis",
                   level="bac_plus_2", section="Sciences expérimentales", bac_year=2023, avg=Decimal("12.10"),
                   interests=["cloud", "cybersécurité"], subjects=["programmation", "réseaux"],
                   goals="Réorientation vers le cycle ingénieur après un L2.", constraints="Travaille à mi-temps.",
                   lang="arabizi", current="L2 Informatique — autre établissement (FICTIF)"),
        "c4": dict(first="Salma", last="Démo", birth=2009, gov="Monastir",
                   level="lycee", section="Sciences expérimentales", bac_year=None, avg=None,
                   interests=["biologie", "informatique"], subjects=["SVT", "mathématiques"],
                   goals="Hésite entre prépa et licence.", constraints=None, lang="fr"),
        "c5": dict(first="Oussama", last="Démo", birth=2007, gov="Sfax",
                   level="bac", section="Économie et gestion", bac_year=2025, avg=Decimal("12.80"),
                   interests=["marketing", "entrepreneuriat"], subjects=["économie", "gestion"],
                   goals="Créer sa propre entreprise.", constraints=None, lang="fr"),
    }
    cands: dict[str, Candidate] = {}
    for key, d in profiles.items():
        c = upsert(s, Candidate, {"user_id": users[key].id}, first_name=d["first"], last_name=d["last"],
                   phone=None, birth_year=d["birth"], governorate=d["gov"], is_demo=True)
        upsert(s, CandidateProfile, {"candidate_id": c.id}, education_level=d["level"], bac_section=d["section"],
               bac_year=d["bac_year"], bac_average=d["avg"], current_program=d.get("current"),
               interests=d["interests"], preferred_subjects=d["subjects"], goals=d["goals"],
               constraints=d["constraints"], preferred_language=d["lang"], is_demo=True)
        for ctype in ("data_processing", "ai_processing", "email_notifications"):
            upsert(s, Consent, {"user_id": users[key].id, "consent_type": ctype, "policy_version": "DEMO-1.0"},
                   granted=True, granted_at=dt(2026, 10, 1), is_demo=True)
        cands[key] = c

    # --- Conversations : français, tunisien (darija), Arabizi, visiteur anonyme
    convs = [
        ("conv-c1", "c1", [
            ("user", "fr", "Bonjour, j'ai un bac maths avec 15 de moyenne. Quelle formation me conseillez-vous en IA ?"),
            ("assistant", "fr", "Avec votre profil, le cycle préparatoire intégré puis le cycle ingénieur Génie Informatique "
                                "sont adaptés (source : Brochure IIT 2026-2027 — DEMO). Une validation par un responsable suivra."),
        ]),
        ("conv-c2", "c2", [
            ("user", "tn_darija", "عسلامة، عندي باك إعلامية. شنوة الفورماسيون اللي تنجم تخدمني بالخف؟"),
            ("assistant", "fr", "La Licence en Informatique (3 ans) peut vous correspondre. Souhaitez-vous connaître les frais ?"),
            ("user", "tn_darija", "إيه، قداش الفلوس متاع العام؟"),
        ]),
        ("conv-c3", "c3", [
            ("user", "arabizi", "3aslema, 3andi L2 info w nheb nodkhol l cycle ingénieur. chnowa lezem na3mel?"),
            ("assistant", "fr", "Vous pouvez déposer une demande d'équivalence (procédure DEMO) puis passer un QCM ciblé."),
        ]),
    ]
    for token, key, msgs in convs:
        conv = upsert(s, Conversation, {"session_token_hash": hash_token(f"demo-{token}")},
                      candidate_id=cands[key].id, status="active", started_at=dt(2026, 10, 2, 10),
                      last_message_at=dt(2026, 10, 2, 10, len(msgs)), attached_at=dt(2026, 10, 2, 10), is_demo=True)
        for i, (sender, lang, content) in enumerate(msgs, start=1):
            upsert(s, Message, {"conversation_id": conv.id, "sequence": i}, sender=sender, channel="text",
                   content=content, detected_language=lang if sender == "user" else "fr",
                   language_confidence=Decimal("0.90") if sender == "user" else None, is_demo=True)

    anon = upsert(s, Conversation, {"session_token_hash": hash_token("demo-conv-anonyme")},
                  candidate_id=None, status="active", started_at=dt(2026, 10, 5, 18),
                  last_message_at=dt(2026, 10, 5, 18, 2), attached_at=None, is_demo=True)
    for i, (sender, channel, lang, content, audio) in enumerate([
        ("user", "audio", "arabizi", "salam, el prepa fi IIT 9adech tdoum?", "demo://audio/anon-1.webm"),
        ("assistant", "text", "fr", "Le cycle préparatoire intégré dure 2 ans (4 semestres) — source : Brochure IIT (DEMO).", None),
        ("user", "text", "fr", "Merci ! Et quelles sont les conditions d'admission ?", None),
    ], start=1):
        upsert(s, Message, {"conversation_id": anon.id, "sequence": i}, sender=sender, channel=channel,
               content=content, detected_language=lang, audio_uri=audio,
               audio_duration_ms=3200 if audio else None, is_demo=True)
    upsert(s, Consent, {"conversation_id": anon.id, "consent_type": "audio_recording", "policy_version": "DEMO-1.0"},
           user_id=None, granted=True, granted_at=dt(2026, 10, 5, 18), is_demo=True)

    resp_iit, resp_ent = users["resp_iit"], users["resp_entretien"]

    # --- Dossier COMPLET (c1) : préinscription + QCM + RDV + entretien + décision
    d1 = upsert(s, Dossier, {"candidate_id": cands["c1"].id, "campaign_id": camp["iit"].id},
                status="decided", ai_summary="Bachelier maths (15,2/20), intérêt IA. QCM 4/5. Entretien favorable. "
                                             "Résumé FICTIF généré par l'agent IA (indicatif).",
                ai_summary_updated_at=dt(2026, 11, 10), is_demo=True)
    upsert(s, Preinscription, {"dossier_id": d1.id, "program_id": p["prepa"].id},
           status="validated", choice_rank=1, submitted_at=dt(2026, 10, 3), is_demo=True)
    upsert(s, Recommendation, {"candidate_id": cands["c1"].id, "program_id": p["prepa"].id},
           conversation_id=None, rank=1, compatibility_score=Decimal("88.50"),
           justification="Bac maths avec bonne moyenne et intérêt pour l'IA : la prépa intégrée mène au cycle ingénieur GI.",
           cited_sources=[{"source_document_id": cat["sources"]["iit_brochure"].id}], model_name="DEMO",
           review_status="confirmed", reviewed_by=resp_iit.id, reviewed_at=dt(2026, 10, 4),
           review_comment=None, is_demo=True)
    q = upsert(s, Qcm, {"dossier_id": d1.id, "title": "QCM de positionnement — Prépa (DEMO)"},
               program_id=p["prepa"].id, generated_by="ai", model_name="DEMO", status="completed",
               score=Decimal("4.00"), max_score=Decimal("5.00"),
               summary_for_interviewer="Bonne maîtrise de l'algèbre ; à consolider : probabilités. (FICTIF)",
               started_at=dt(2026, 10, 10, 14), completed_at=dt(2026, 10, 10, 14, 25), is_demo=True)
    questions = [
        ("mathématiques", "Quelle est la dérivée de x² ?", ["x", "2x", "x²", "2"], 1, 1),
        ("mathématiques", "Combien vaut log10(1000) ?", ["2", "3", "10", "100"], 1, 1),
        ("probabilités", "On lance une pièce 2 fois : probabilité d'obtenir 2 piles ?", ["1/2", "1/3", "1/4", "1"], 2, 0),
        ("logique", "Si A ⇒ B et B est faux, alors :", ["A est vrai", "A est faux", "on ne sait pas"], 1, 1),
        ("informatique", "Quelle structure suit le principe FIFO ?", ["Pile", "File", "Arbre"], 1, 1),
    ]
    for pos, (topic, text_, choices, correct, selected_ok) in enumerate(questions, start=1):
        qq = upsert(s, QcmQuestion, {"qcm_id": q.id, "position": pos}, topic=topic, question_text=text_,
                    choices=choices, correct_choice_index=correct, points=Decimal("1"), is_demo=True)
        selected = correct if selected_ok else (correct + 1) % len(choices)
        upsert(s, QcmAnswer, {"question_id": qq.id}, selected_choice_index=selected, is_correct=bool(selected_ok),
               points_awarded=Decimal("1") if selected_ok else Decimal("0"),
               answered_at=dt(2026, 10, 10, 14, 5 * pos), is_demo=True)
    a1 = upsert(s, Appointment, {"dossier_id": d1.id, "scheduled_at": dt(2026, 10, 20, 10)},
                organizer_id=resp_ent.id, duration_minutes=30, mode="on_site", location="IIT — salle DEMO",
                status="completed", is_demo=True)
    upsert(s, InterviewResult, {"appointment_id": a1.id}, interviewer_id=resp_ent.id,
           observations="Candidat motivé, projet clair. (FICTIF)", score=Decimal("16.00"), opinion="favorable",
           recorded_at=dt(2026, 10, 20, 10, 40), is_demo=True)
    dec = upsert(s, Decision, {"dossier_id": d1.id}, program_id=p["prepa"].id, decision="admitted",
                 observations="Admis en cycle préparatoire intégré. (FICTIF)", responsible_id=resp_iit.id,
                 decided_at=dt(2026, 11, 5), is_demo=True)
    upsert(s, Notification, {"user_id": users["c1"].id, "dossier_id": d1.id, "kind": "decision"},
           channel="email", template_code="decision_admitted", subject="Votre dossier : décision disponible (DEMO)",
           scheduled_for=dt(2026, 11, 5, 12), status="sent", attempts=1, sent_at=dt(2026, 11, 5, 12, 1), is_demo=True)

    # --- c2 : préinscription soumise + recommandation EN ATTENTE de validation
    d2 = upsert(s, Dossier, {"candidate_id": cands["c2"].id, "campaign_id": camp["iit"].id},
                status="in_progress", ai_summary=None, ai_summary_updated_at=None, is_demo=True)
    upsert(s, Preinscription, {"dossier_id": d2.id, "program_id": p["lic"].id},
           status="submitted", choice_rank=1, submitted_at=dt(2026, 10, 6), is_demo=True)
    upsert(s, Recommendation, {"candidate_id": cands["c2"].id, "program_id": p["lic"].id},
           conversation_id=None, rank=1, compatibility_score=Decimal("81.00"),
           justification="Bac informatique et souhait d'insertion rapide : la licence en 3 ans est adaptée.",
           cited_sources=[{"source_document_id": cat["sources"]["iit_brochure"].id}], model_name="DEMO",
           review_status="pending", reviewed_by=None, reviewed_at=None, review_comment=None, is_demo=True)
    upsert(s, Appointment, {"dossier_id": d2.id, "scheduled_at": dt(2027, 1, 15, 11)},
           organizer_id=resp_ent.id, duration_minutes=30, mode="online",
           meeting_url="https://meet.demo.smartcampus.invalid/rdv-demo", status="scheduled", is_demo=True)

    # --- c3 : demande d'équivalence (réorientation L2 -> cycle ingénieur)
    d3 = upsert(s, Dossier, {"candidate_id": cands["c3"].id, "campaign_id": camp["iit"].id},
                status="in_progress", ai_summary=None, ai_summary_updated_at=None, is_demo=True)
    eq = upsert(s, EquivalenceRequest, {"dossier_id": d3.id, "target_program_id": p["ing"].id},
                origin_diploma="L2 Informatique (FICTIF)", origin_program="Licence Informatique",
                origin_institution="Établissement d'origine FICTIF", origin_country="TN",
                origin_level="bac_plus_2", requested_entry_level="1ère année cycle ingénieur",
                status="under_review", submitted_at=dt(2026, 10, 8), reviewed_by=None, reviewed_at=None,
                review_comment=None, is_demo=True)
    for doc_type, name in [("transcript", "releve_notes_L2_demo.pdf"), ("diploma", "attestation_L2_demo.pdf")]:
        upsert(s, EquivalenceDocument, {"storage_key": f"demo/equivalences/{eq.id}/{name}"},
               equivalence_request_id=eq.id, document_type=doc_type, file_name=name, mime_type="application/pdf",
               size_bytes=125_000, sha256=demo_hash("equiv", name), is_demo=True)
    upsert(s, Recommendation, {"candidate_id": cands["c3"].id, "program_id": p["ing"].id},
           conversation_id=None, rank=1, compatibility_score=Decimal("74.00"),
           justification="L2 informatique validé : accès possible au cycle ingénieur via passerelle et équivalence.",
           cited_sources=[{"source_document_id": cat["sources"]["equiv"].id}], model_name="DEMO",
           review_status="adjusted", reviewed_by=resp_iit.id, reviewed_at=dt(2026, 10, 9),
           review_comment="Conditionné à l'acceptation de l'équivalence et au QCM. (FICTIF)", is_demo=True)

    # --- c4 : dossier ouvert + relance programmée
    d4 = upsert(s, Dossier, {"candidate_id": cands["c4"].id, "campaign_id": camp["iit"].id},
                status="open", ai_summary=None, ai_summary_updated_at=None, is_demo=True)
    upsert(s, Preinscription, {"dossier_id": d4.id, "program_id": p["prepa"].id},
           status="draft", choice_rank=1, submitted_at=None, is_demo=True)
    upsert(s, Notification, {"user_id": users["c4"].id, "dossier_id": d4.id, "kind": "reminder"},
           channel="email", template_code="reminder_incomplete_dossier",
           subject="Votre préinscription n'est pas encore soumise (DEMO)", scheduled_for=dt(2026, 12, 1, 9),
           status="pending", attempts=0, sent_at=None, is_demo=True)

    # --- c5 : candidat ISB
    d5 = upsert(s, Dossier, {"candidate_id": cands["c5"].id, "campaign_id": camp["isb"].id},
                status="in_progress", ai_summary=None, ai_summary_updated_at=None, is_demo=True)
    upsert(s, Preinscription, {"dossier_id": d5.id, "program_id": p["isb_lic"].id},
           status="submitted", choice_rank=1, submitted_at=dt(2026, 10, 12), is_demo=True)

    for action, etype, eid, actor in [
        ("decision.create", "decisions", dec.id, resp_iit.id),
        ("recommendation.review", "dossiers", d1.id, resp_iit.id),
        ("equivalence.submit", "equivalence_requests", eq.id, users["c3"].id),
    ]:
        if s.scalars(select(AuditLog).filter_by(action=action, entity_type=etype, entity_id=eid)).first() is None:
            s.add(AuditLog(actor_type="user", actor_user_id=actor, action=action, entity_type=etype, entity_id=eid,
                           details={"demo": True}, occurred_at=dt(2026, 11, 5)))
    s.flush()


# ============================================================================ Documents RAG
def seed_documents(s: Session, cat: dict[str, Any], users: dict[str, User]) -> None:
    src, p = cat["sources"], cat["programs"]
    chunks = {
        "iit_brochure": [
            ("Présentation", None, "L'IIT propose une licence, un cycle préparatoire intégré et un cycle ingénieur. (DEMO)"),
            ("Cycle préparatoire", "prepa", "Le cycle préparatoire intégré dure 2 ans et prépare au cycle ingénieur. (DEMO)"),
            ("Licence", "lic", "La licence en informatique dure 3 ans ; frais FICTIFS : 5 900 TND/an. (DEMO)"),
        ],
        "iit_ing": [
            ("Programme", "ing", "Le cycle ingénieur GI couvre génie logiciel, IA, cloud et sécurité. (DEMO)"),
            ("Admission", "ing", "Admission sur dossier Bac+2, QCM ciblé et entretien. (DEMO)"),
        ],
        "iit_faq": [
            ("Rendez-vous", None, "Après la préinscription, un rendez-vous d'orientation est proposé. (DEMO)"),
        ],
        "equiv": [
            ("Pièces", None, "Joindre relevés de notes, diplôme ou attestation et programme suivi. (DEMO)"),
            ("Décision", None, "La demande est vérifiée par un responsable ; l'IA ne décide jamais. (DEMO)"),
        ],
        "isb_brochure": [
            ("Licence Gestion", "isb_lic", "La licence en gestion dure 3 ans. (DEMO)"),
            ("Master Marketing", "isb_mas", "Le master marketing digital dure 2 ans, en mode hybride. (DEMO)"),
        ],
    }
    for key, items in chunks.items():
        for idx, (section, prog, content) in enumerate(items):
            upsert(s, DocumentChunk, {"source_document_id": src[key].id, "chunk_index": idx},
                   program_id=p[prog].id if prog else None, content=content, section_title=section,
                   page_number=idx + 1, token_count=len(content.split()), embedding=fake_embedding(f"{key}:{idx}"),
                   embedding_model="DEMO-fake-embedding", chunk_metadata={"demo": True}, is_demo=True)

    job = s.scalars(select(SyncJob).filter_by(job_type="full_sync", started_at=dt(2026, 10, 1, 2))).first()
    if job is None:
        job = SyncJob(job_type="full_sync", status="succeeded", triggered_by=users["admin"].id,
                      started_at=dt(2026, 10, 1, 2), finished_at=dt(2026, 10, 1, 2, 3),
                      processed_count=sum(len(v) for v in chunks.values()), error_count=0)
        s.add(job)
        s.flush()
        s.add_all([
            SyncLog(sync_job_id=job.id, level="info", message="Synchronisation DEMO démarrée.", details=None),
            SyncLog(sync_job_id=job.id, level="info", message="5 documents DEMO traités.", details={"documents": 5}),
        ])
        s.flush()


def run_seed(session: Session) -> None:
    cat = seed_catalog(session)
    users = seed_users(session, cat)
    seed_candidates(session, cat, users)
    seed_documents(session, cat, users)


def main() -> None:
    engine = create_engine(get_settings().migration_database_url)
    with Session(engine) as session, session.begin():
        run_seed(session)
    engine.dispose()
    print("Seed DEMO appliqué (idempotent).")


if __name__ == "__main__":
    main()
