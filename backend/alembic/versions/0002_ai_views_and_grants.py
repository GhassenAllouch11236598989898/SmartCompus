"""SA-16/17 — schéma ai_views (outil SQL de l'agent IA) et privilèges des rôles applicatifs.

Revision ID: 0002_ai_views_and_grants
Revises: 0001_initial_schema
Create Date: 2026-11-23
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002_ai_views_and_grants"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_COLS = """
    sd.id            AS source_document_id,
    sd.title         AS source_title,
    sd.doc_type::text AS source_type,
    sd.version       AS source_version,
    sd.document_date AS source_date"""

VIEWS: dict[str, str] = {
    "v_formations_public": f"""
SELECT
    p.id AS formation_id, p.code, p.title, p.summary, p.description,
    i.code AS institution_code, i.name AS institution_name,
    pt.code AS program_type_code, pt.label AS program_type_label,
    p.duration_semesters, p.study_mode::text AS study_mode, p.teaching_language, p.diploma_awarded,
    p.is_demo, p.updated_at,{SOURCE_COLS}
FROM public.programs p
JOIN public.institutions i ON i.id = p.institution_id
JOIN public.program_types pt ON pt.id = p.program_type_id
JOIN public.source_documents sd ON sd.id = p.source_document_id
WHERE p.status = 'published'
""",
    "v_tuition_fees_public": f"""
SELECT
    f.id AS tuition_fee_id, p.id AS formation_id, p.code AS formation_code, p.title AS formation_title,
    f.academic_year, f.fee_type::text AS fee_type, f.amount, f.currency, f.payment_terms,
    f.is_demo, f.updated_at,{SOURCE_COLS}
FROM public.tuition_fees f
JOIN public.programs p ON p.id = f.program_id AND p.status = 'published'
JOIN public.source_documents sd ON sd.id = f.source_document_id
""",
    "v_admission_conditions_public": f"""
SELECT
    c.id AS condition_id, p.id AS formation_id, p.code AS formation_code, p.title AS formation_title,
    c.academic_year, c.kind::text AS kind, c.description, c.minimum_average, c.eligible_bac_sections,
    c.position, c.is_demo, c.updated_at,{SOURCE_COLS}
FROM public.admission_conditions c
JOIN public.programs p ON p.id = c.program_id AND p.status = 'published'
JOIN public.source_documents sd ON sd.id = c.source_document_id
""",
    "v_prerequisites_public": f"""
SELECT
    r.id AS prerequisite_id, p.id AS formation_id, p.code AS formation_code,
    r.kind::text AS kind, r.label, r.description, r.is_mandatory, r.is_demo, r.updated_at,{SOURCE_COLS}
FROM public.program_prerequisites r
JOIN public.programs p ON p.id = r.program_id AND p.status = 'published'
JOIN public.source_documents sd ON sd.id = r.source_document_id
""",
    "v_career_outcomes_public": f"""
SELECT
    o.id AS career_outcome_id, p.id AS formation_id, p.code AS formation_code,
    o.title, o.sector, o.description, o.is_demo, o.updated_at,{SOURCE_COLS}
FROM public.career_outcomes o
JOIN public.programs p ON p.id = o.program_id AND p.status = 'published'
JOIN public.source_documents sd ON sd.id = o.source_document_id
""",
    "v_pathways_public": f"""
SELECT
    w.id AS pathway_id,
    pf.id AS from_formation_id, pf.code AS from_formation_code, pf.title AS from_formation_title,
    pt.id AS to_formation_id, pt.code AS to_formation_code, pt.title AS to_formation_title,
    w.entry_level, w.conditions, w.is_demo, w.updated_at,{SOURCE_COLS}
FROM public.program_pathways w
JOIN public.programs pf ON pf.id = w.from_program_id AND pf.status = 'published'
JOIN public.programs pt ON pt.id = w.to_program_id AND pt.status = 'published'
JOIN public.source_documents sd ON sd.id = w.source_document_id
""",
    # Aucune donnée d'identité (nom, email, téléphone), aucun consentement, aucun message.
    "v_candidate_dossier_summary": """
SELECT
    d.id AS dossier_id,
    d.candidate_id,
    d.status::text AS dossier_status,
    c.academic_year,
    i.code AS institution_code,
    (SELECT string_agg(p.title || ' [' || pr.status::text || ']', ' | ' ORDER BY pr.choice_rank)
       FROM public.preinscriptions pr JOIN public.programs p ON p.id = pr.program_id
      WHERE pr.dossier_id = d.id) AS preinscriptions,
    (SELECT e.status::text FROM public.equivalence_requests e
      WHERE e.dossier_id = d.id ORDER BY e.submitted_at DESC LIMIT 1) AS last_equivalence_status,
    (SELECT q.score FROM public.qcm q
      WHERE q.dossier_id = d.id AND q.status = 'completed' ORDER BY q.completed_at DESC LIMIT 1) AS last_qcm_score,
    (SELECT q.max_score FROM public.qcm q
      WHERE q.dossier_id = d.id AND q.status = 'completed' ORDER BY q.completed_at DESC LIMIT 1) AS last_qcm_max_score,
    (SELECT min(a.scheduled_at) FROM public.appointments a
      WHERE a.dossier_id = d.id AND a.status IN ('scheduled', 'confirmed') AND a.scheduled_at >= now())
        AS next_appointment_at,
    (SELECT dc.decision::text FROM public.decisions dc
      WHERE dc.dossier_id = d.id ORDER BY dc.decided_at DESC LIMIT 1) AS last_decision,
    d.ai_summary,
    d.ai_summary_updated_at,
    d.is_demo,
    d.updated_at
FROM public.dossiers d
JOIN public.admission_campaigns c ON c.id = d.campaign_id
JOIN public.institutions i ON i.id = c.institution_id
""",
}

APP_ROLE = "smartcampus_app"
AI_ROLE = "ai_readonly"
APP_DELETE_TABLES = ("user_roles", "document_chunks")


def _if_role(role: str, sql: str) -> str:
    """Exécute un bloc seulement si le rôle existe (bases créées hors docker)."""
    return f"""
DO $do$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
        {sql}
    END IF;
END $do$;
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ai_views")
    op.execute("REVOKE ALL ON SCHEMA ai_views FROM PUBLIC")
    for name, body in VIEWS.items():
        op.execute(f"CREATE VIEW ai_views.{name} WITH (security_barrier = true) AS {body}")
        op.execute(f"REVOKE ALL ON ai_views.{name} FROM PUBLIC")

    # Rôle applicatif : DML sans DELETE (sauf exceptions documentées), pas de DDL.
    op.execute(
        _if_role(
            APP_ROLE,
            f"""
        EXECUTE 'GRANT USAGE ON SCHEMA public TO {APP_ROLE}';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}';
        EXECUTE 'GRANT DELETE ON {", ".join(APP_DELETE_TABLES)} TO {APP_ROLE}';
        EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE ON TABLES TO {APP_ROLE}';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}';
        """,
        )
    )
    # Rôle IA : lecture des seules vues ai_views ; aucun accès explicite à public.
    op.execute(
        _if_role(
            AI_ROLE,
            f"""
        EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {AI_ROLE}';
        EXECUTE 'REVOKE ALL ON SCHEMA public FROM {AI_ROLE}';
        EXECUTE 'GRANT USAGE ON SCHEMA ai_views TO {AI_ROLE}';
        EXECUTE 'GRANT SELECT ON ALL TABLES IN SCHEMA ai_views TO {AI_ROLE}';
        """,
        )
    )


def downgrade() -> None:
    op.execute(
        _if_role(
            APP_ROLE,
            f"""
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE ON TABLES FROM {APP_ROLE}';
        EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM {APP_ROLE}';
        EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {APP_ROLE}';
        EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {APP_ROLE}';
        """,
        )
    )
    op.execute("DROP SCHEMA IF EXISTS ai_views CASCADE")
