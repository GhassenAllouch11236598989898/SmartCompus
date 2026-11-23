"""SA-17 — schéma initial : catalogue, utilisateurs/candidatures, documents/RAG + règles métier en base.

Le code des tables a été rendu depuis les modèles (alembic.autogenerate.render_python_code), puis figé :
cette migration ne dépend plus des modèles et reste reproductible.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENUMS = {
    'actor_type': ('user', 'ai_agent', 'system'),
    'admission_condition_kind': ('dossier_review', 'minimum_average', 'entrance_exam', 'qcm', 'interview', 'equivalence', 'other'),
    'appointment_mode': ('on_site', 'online', 'phone'),
    'appointment_status': ('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show'),
    'campaign_status': ('planned', 'open', 'closed'),
    'consent_type': ('data_processing', 'ai_processing', 'audio_recording', 'email_notifications'),
    'conversation_status': ('active', 'closed'),
    'decision_value': ('admitted', 'admitted_with_conditions', 'waitlisted', 'rejected'),
    'dossier_status': ('open', 'in_progress', 'interview_scheduled', 'decision_pending', 'decided', 'enrolled', 'withdrawn', 'closed'),
    'education_level': ('lycee', 'bac', 'bac_plus_1', 'bac_plus_2', 'bac_plus_3', 'bac_plus_4_or_more', 'other'),
    'equivalence_document_type': ('diploma', 'transcript', 'syllabus', 'identity', 'other'),
    'equivalence_status': ('submitted', 'under_review', 'accepted', 'rejected', 'more_info_requested'),
    'fee_type': ('registration', 'tuition', 'exam', 'other'),
    'interview_opinion': ('favorable', 'reserved', 'unfavorable'),
    'message_channel': ('text', 'audio'),
    'message_language': ('fr', 'ar', 'tn_darija', 'arabizi', 'en', 'mixed', 'unknown'),
    'message_sender': ('user', 'assistant', 'system'),
    'notification_channel': ('email', 'in_app'),
    'notification_kind': ('reminder', 'confirmation', 'appointment', 'decision', 'other'),
    'notification_status': ('pending', 'sent', 'failed', 'cancelled'),
    'preinscription_status': ('draft', 'submitted', 'under_review', 'validated', 'rejected', 'cancelled'),
    'prerequisite_kind': ('diploma', 'level', 'subject', 'skill'),
    'program_status': ('draft', 'published', 'archived'),
    'qcm_generated_by': ('ai', 'template'),
    'qcm_status': ('generated', 'in_progress', 'completed', 'expired'),
    'review_status': ('pending', 'confirmed', 'adjusted'),
    'role_code': ('candidate', 'responsable_iit', 'responsable_isb', 'responsable_entretien', 'direction', 'admin'),
    'source_document_status': ('draft', 'active', 'superseded', 'archived'),
    'source_document_type': ('brochure', 'faq', 'procedure', 'programme'),
    'study_mode': ('on_site', 'hybrid', 'online', 'work_study'),
    'sync_job_type': ('ingest', 'reindex', 'full_sync'),
    'sync_log_level': ('info', 'warning', 'error'),
    'sync_status': ('pending', 'running', 'succeeded', 'failed', 'partial'),
}

TABLES = ['institutions', 'program_types', 'status_history', 'users', 'audit_log', 'candidates', 'roles', 'source_documents', 'admission_campaigns', 'candidate_profiles', 'conversations', 'programs', 'sync_jobs', 'user_roles', 'admission_conditions', 'career_outcomes', 'consents', 'document_chunks', 'dossiers', 'messages', 'program_pathways', 'program_prerequisites', 'recommendations', 'sync_logs', 'tuition_fees', 'appointments', 'decisions', 'equivalence_requests', 'notifications', 'preinscriptions', 'qcm', 'equivalence_documents', 'interview_results', 'qcm_questions', 'qcm_answers']

# Tables dotées d'une colonne updated_at => trigger set_updated_at.
UPDATED_AT_TABLES = ['institutions', 'program_types', 'users', 'candidates', 'roles', 'source_documents', 'admission_campaigns', 'candidate_profiles', 'conversations', 'programs', 'sync_jobs', 'admission_conditions', 'career_outcomes', 'consents', 'document_chunks', 'dossiers', 'messages', 'program_pathways', 'program_prerequisites', 'recommendations', 'tuition_fees', 'appointments', 'decisions', 'equivalence_requests', 'notifications', 'preinscriptions', 'qcm', 'equivalence_documents', 'interview_results', 'qcm_questions', 'qcm_answers']

# Aucune suppression physique (archivage par statut). Exceptions : user_roles (retrait d'un rôle)
# et document_chunks (re-découpage d'un document par le pipeline RAG).
NO_DELETE_TABLES = [t for t in TABLES if t not in ("user_roles", "document_chunks")]

# Journaux append-only (ni UPDATE ni DELETE).
APPEND_ONLY_TABLES = ["audit_log", "status_history", "sync_logs"]

# (table, colonne de statut) historisées automatiquement dans status_history.
STATUS_TRACKED = [
    ("programs", "status"),
    ("dossiers", "status"),
    ("preinscriptions", "status"),
    ("equivalence_requests", "status"),
    ("qcm", "status"),
    ("appointments", "status"),
    ("recommendations", "review_status"),
    ("notifications", "status"),
]

# (table, colonne utilisateur) qui doivent référencer un responsable HUMAIN actif.
HUMAN_RESPONSABLE_COLUMNS = [
    ("decisions", "responsible_id"),
    ("recommendations", "reviewed_by"),
    ("equivalence_requests", "reviewed_by"),
    ("interview_results", "interviewer_id"),
]

FUNCTIONS_SQL = r"""
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION prevent_delete() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
    RAISE EXCEPTION 'Suppression physique interdite sur "%" : utiliser un statut (archivage/historique).', TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
END $$;

CREATE OR REPLACE FUNCTION prevent_update_delete() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
    RAISE EXCEPTION 'Table "%" en ajout seul (append-only) : % interdit.', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END $$;

CREATE OR REPLACE FUNCTION log_status_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE
    col     text := TG_ARGV[0];
    old_val text;
    new_val text := to_jsonb(NEW) ->> col;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        old_val := to_jsonb(OLD) ->> col;
        IF old_val IS NOT DISTINCT FROM new_val THEN
            RETURN NEW;
        END IF;
    END IF;
    INSERT INTO status_history (entity_type, entity_id, old_status, new_status, changed_by)
    VALUES (TG_TABLE_NAME, NEW.id, old_val, new_val,
            NULLIF(current_setting('app.current_user_id', true), '')::bigint);
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION assert_human_responsable() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE
    col text := TG_ARGV[0];
    uid bigint := (to_jsonb(NEW) ->> col)::bigint;
BEGIN
    IF uid IS NULL THEN
        RETURN NEW;
    END IF;
    IF NOT EXISTS (
        SELECT 1
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE u.id = uid
          AND u.is_active
          AND NOT u.is_service_account
          AND r.code IN ('responsable_iit', 'responsable_isb', 'responsable_entretien')
    ) THEN
        RAISE EXCEPTION '%.% : l''utilisateur % doit être un responsable humain actif (aucune décision par un agent IA).',
            TG_TABLE_NAME, col, uid
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
"""

FUNCTION_NAMES = [
    "set_updated_at()",
    "prevent_delete()",
    "prevent_update_delete()",
    "log_status_change()",
    "assert_human_responsable()",
]


def _create_triggers() -> None:
    op.execute(FUNCTIONS_SQL)
    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )
    for table in NO_DELETE_TABLES:
        if table in APPEND_ONLY_TABLES:
            continue
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_delete BEFORE DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION prevent_delete()"
        )
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION prevent_update_delete()"
        )
    for table, col in STATUS_TRACKED:
        op.execute(
            f"CREATE TRIGGER trg_{table}_status_history AFTER INSERT OR UPDATE OF {col} ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION log_status_change('{col}')"
        )
    for table, col in HUMAN_RESPONSABLE_COLUMNS:
        op.execute(
            f"CREATE TRIGGER trg_{table}_{col}_human BEFORE INSERT OR UPDATE OF {col} ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION assert_human_responsable('{col}')"
        )


def upgrade() -> None:
    # pgvector est installé par le script d'init (superuser) ; no-op s'il existe déjà.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    op.create_table('institutions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('website', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("code ~ '^[A-Z0-9_]{2,20}$'", name=op.f('ck_institutions_code_format')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_institutions')),
    sa.UniqueConstraint('code', name=op.f('uq_institutions_code'))
    )
    op.create_table('program_types',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=False),
    sa.Column('label', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("code ~ '^[A-Z0-9_]{2,30}$'", name=op.f('ck_program_types_code_format')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program_types')),
    sa.UniqueConstraint('code', name=op.f('uq_program_types_code'))
    )
    op.create_table('status_history',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('entity_type', sa.String(length=100), nullable=False),
    sa.Column('entity_id', sa.BigInteger(), nullable=False),
    sa.Column('old_status', sa.String(length=50), nullable=True),
    sa.Column('new_status', sa.String(length=50), nullable=False),
    sa.Column('changed_by', sa.BigInteger(), nullable=True),
    sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_status_history'))
    )
    op.create_index('ix_status_history_entity', 'status_history', ['entity_type', 'entity_id', 'changed_at'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('is_service_account', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("password_hash IS NULL OR password_hash ~ '^\\$(2[aby]|argon2id?)\\$'", name=op.f('ck_users_password_hashed')),
    sa.CheckConstraint("position('@' in email) > 1", name=op.f('ck_users_email_format')),
    sa.CheckConstraint('NOT is_service_account OR password_hash IS NULL', name=op.f('ck_users_service_account_no_password')),
    sa.CheckConstraint('email = lower(email)', name=op.f('ck_users_email_lowercase')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email'))
    )
    op.create_table('audit_log',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('actor_type', postgresql.ENUM('user', 'ai_agent', 'system', name='actor_type', create_type=False), nullable=False),
    sa.Column('actor_user_id', sa.BigInteger(), nullable=True),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('entity_type', sa.String(length=100), nullable=False),
    sa.Column('entity_id', sa.BigInteger(), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('request_id', sa.String(length=64), nullable=True),
    sa.CheckConstraint("actor_type <> 'user' OR actor_user_id IS NOT NULL", name=op.f('ck_audit_log_user_actor_has_id')),
    sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], name=op.f('fk_audit_log_actor_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index(op.f('ix_audit_log_actor_user_id'), 'audit_log', ['actor_user_id'], unique=False)
    op.create_index('ix_audit_log_entity', 'audit_log', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_audit_log_occurred_at', 'audit_log', ['occurred_at'], unique=False)
    op.create_table('candidates',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('birth_year', sa.SmallInteger(), nullable=True),
    sa.Column('governorate', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("phone IS NULL OR phone ~ '^\\+?[0-9 ]{8,20}$'", name=op.f('ck_candidates_phone_format')),
    sa.CheckConstraint('birth_year IS NULL OR birth_year BETWEEN 1950 AND 2020', name=op.f('ck_candidates_birth_year_range')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_candidates_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_candidates')),
    sa.UniqueConstraint('user_id', name=op.f('uq_candidates_user_id'))
    )
    op.create_table('roles',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('code', postgresql.ENUM('candidate', 'responsable_iit', 'responsable_isb', 'responsable_entretien', 'direction', 'admin', name='role_code', create_type=False), nullable=False),
    sa.Column('label', sa.String(length=100), nullable=False),
    sa.Column('institution_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_roles_institution_id_institutions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
    sa.UniqueConstraint('code', name=op.f('uq_roles_code'))
    )
    op.create_table('source_documents',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('institution_id', sa.BigInteger(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('doc_type', postgresql.ENUM('brochure', 'faq', 'procedure', 'programme', name='source_document_type', create_type=False), nullable=False),
    sa.Column('version', sa.String(length=50), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'active', 'superseded', 'archived', name='source_document_status', create_type=False), server_default='draft', nullable=False),
    sa.Column('uri', sa.String(length=1024), nullable=True),
    sa.Column('language', sa.String(length=10), server_default='fr', nullable=False),
    sa.Column('document_date', sa.Date(), nullable=True),
    sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name=op.f('ck_source_documents_content_hash_sha256')),
    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_source_documents_institution_id_institutions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_source_documents')),
    sa.UniqueConstraint('content_hash', name=op.f('uq_source_documents_content_hash')),
    sa.UniqueConstraint('title', 'version', name=op.f('uq_source_documents_title_version'))
    )
    op.create_index(op.f('ix_source_documents_institution_id'), 'source_documents', ['institution_id'], unique=False)
    op.create_table('admission_campaigns',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('institution_id', sa.BigInteger(), nullable=False),
    sa.Column('academic_year', sa.String(length=9), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('opens_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('closes_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', postgresql.ENUM('planned', 'open', 'closed', name='campaign_status', create_type=False), server_default='planned', nullable=False),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("academic_year ~ '^[0-9]{4}-[0-9]{4}$'", name=op.f('ck_admission_campaigns_academic_year_format')),
    sa.CheckConstraint('closes_at > opens_at', name=op.f('ck_admission_campaigns_dates_order')),
    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_admission_campaigns_institution_id_institutions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_admission_campaigns_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admission_campaigns')),
    sa.UniqueConstraint('institution_id', 'academic_year', 'name', name=op.f('uq_admission_campaigns_institution_id_academic_year_name'))
    )
    op.create_index(op.f('ix_admission_campaigns_institution_id'), 'admission_campaigns', ['institution_id'], unique=False)
    op.create_index(op.f('ix_admission_campaigns_source_document_id'), 'admission_campaigns', ['source_document_id'], unique=False)
    op.create_table('candidate_profiles',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('candidate_id', sa.BigInteger(), nullable=False),
    sa.Column('education_level', postgresql.ENUM('lycee', 'bac', 'bac_plus_1', 'bac_plus_2', 'bac_plus_3', 'bac_plus_4_or_more', 'other', name='education_level', create_type=False), nullable=True),
    sa.Column('bac_section', sa.String(length=50), nullable=True),
    sa.Column('bac_year', sa.SmallInteger(), nullable=True),
    sa.Column('bac_average', sa.Numeric(precision=4, scale=2), nullable=True),
    sa.Column('current_program', sa.String(length=255), nullable=True),
    sa.Column('interests', postgresql.ARRAY(sa.String(length=100)), server_default='{}', nullable=False),
    sa.Column('preferred_subjects', postgresql.ARRAY(sa.String(length=100)), server_default='{}', nullable=False),
    sa.Column('goals', sa.Text(), nullable=True),
    sa.Column('constraints', sa.Text(), nullable=True),
    sa.Column('preferred_language', postgresql.ENUM('fr', 'ar', 'tn_darija', 'arabizi', 'en', 'mixed', 'unknown', name='message_language', create_type=False), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('bac_average IS NULL OR bac_average BETWEEN 0 AND 20', name=op.f('ck_candidate_profiles_bac_average_range')),
    sa.CheckConstraint('bac_year IS NULL OR bac_year BETWEEN 1980 AND 2100', name=op.f('ck_candidate_profiles_bac_year_range')),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_candidate_profiles_candidate_id_candidates'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_candidate_profiles')),
    sa.UniqueConstraint('candidate_id', name=op.f('uq_candidate_profiles_candidate_id'))
    )
    op.create_table('conversations',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('candidate_id', sa.BigInteger(), nullable=True),
    sa.Column('session_token_hash', sa.String(length=64), nullable=False),
    sa.Column('status', postgresql.ENUM('active', 'closed', name='conversation_status', create_type=False), server_default='active', nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('attached_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("session_token_hash ~ '^[0-9a-f]{64}$'", name=op.f('ck_conversations_session_token_sha256')),
    sa.CheckConstraint('candidate_id IS NULL OR attached_at IS NOT NULL', name=op.f('ck_conversations_attached_has_date')),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_conversations_candidate_id_candidates'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_conversations')),
    sa.UniqueConstraint('session_token_hash', name=op.f('uq_conversations_session_token_hash'))
    )
    op.create_index(op.f('ix_conversations_candidate_id'), 'conversations', ['candidate_id'], unique=False)
    op.create_table('programs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('institution_id', sa.BigInteger(), nullable=False),
    sa.Column('program_type_id', sa.BigInteger(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('summary', sa.String(length=500), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('duration_semesters', sa.Integer(), nullable=False),
    sa.Column('study_mode', postgresql.ENUM('on_site', 'hybrid', 'online', 'work_study', name='study_mode', create_type=False), server_default='on_site', nullable=False),
    sa.Column('teaching_language', sa.String(length=50), server_default='fr', nullable=False),
    sa.Column('diploma_awarded', sa.String(length=255), nullable=True),
    sa.Column('status', postgresql.ENUM('draft', 'published', 'archived', name='program_status', create_type=False), server_default='draft', nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('french', coalesce(title,'') || ' ' || coalesce(summary,'') || ' ' || coalesce(description,''))", persisted=True), nullable=True),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("(status <> 'published') OR (published_at IS NOT NULL)", name=op.f('ck_programs_published_has_date')),
    sa.CheckConstraint("code ~ '^[A-Z0-9_-]{2,40}$'", name=op.f('ck_programs_code_format')),
    sa.CheckConstraint('duration_semesters BETWEEN 1 AND 12', name=op.f('ck_programs_duration_range')),
    sa.ForeignKeyConstraint(['institution_id'], ['institutions.id'], name=op.f('fk_programs_institution_id_institutions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['program_type_id'], ['program_types.id'], name=op.f('fk_programs_program_type_id_program_types'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_programs_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_programs')),
    sa.UniqueConstraint('code', name=op.f('uq_programs_code'))
    )
    op.create_index(op.f('ix_programs_institution_id'), 'programs', ['institution_id'], unique=False)
    op.create_index('ix_programs_institution_status', 'programs', ['institution_id', 'status'], unique=False)
    op.create_index(op.f('ix_programs_program_type_id'), 'programs', ['program_type_id'], unique=False)
    op.create_index('ix_programs_search_vector', 'programs', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_programs_source_document_id'), 'programs', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_programs_status'), 'programs', ['status'], unique=False)
    op.create_table('sync_jobs',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('source_document_id', sa.BigInteger(), nullable=True),
    sa.Column('job_type', postgresql.ENUM('ingest', 'reindex', 'full_sync', name='sync_job_type', create_type=False), nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'running', 'succeeded', 'failed', 'partial', name='sync_status', create_type=False), server_default='pending', nullable=False),
    sa.Column('triggered_by', sa.BigInteger(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('processed_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('error_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status NOT IN ('succeeded', 'failed', 'partial') OR finished_at IS NOT NULL", name=op.f('ck_sync_jobs_terminal_has_end')),
    sa.CheckConstraint('error_count >= 0 AND processed_count >= 0', name=op.f('ck_sync_jobs_counters_positive')),
    sa.CheckConstraint('finished_at IS NULL OR finished_at >= started_at', name=op.f('ck_sync_jobs_dates_order')),
    sa.CheckConstraint('finished_at IS NULL OR started_at IS NOT NULL', name=op.f('ck_sync_jobs_finished_after_start')),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_sync_jobs_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['triggered_by'], ['users.id'], name=op.f('fk_sync_jobs_triggered_by_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sync_jobs'))
    )
    op.create_index(op.f('ix_sync_jobs_source_document_id'), 'sync_jobs', ['source_document_id'], unique=False)
    op.create_index('ix_sync_jobs_status_created', 'sync_jobs', ['status', 'created_at'], unique=False)
    op.create_table('user_roles',
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('role_id', sa.BigInteger(), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('granted_by', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['granted_by'], ['users.id'], name=op.f('fk_user_roles_granted_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_roles_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles'))
    )
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'], unique=False)
    op.create_table('admission_conditions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=False),
    sa.Column('academic_year', sa.String(length=9), nullable=True),
    sa.Column('kind', postgresql.ENUM('dossier_review', 'minimum_average', 'entrance_exam', 'qcm', 'interview', 'equivalence', 'other', name='admission_condition_kind', create_type=False), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('minimum_average', sa.Numeric(precision=4, scale=2), nullable=True),
    sa.Column('eligible_bac_sections', postgresql.ARRAY(sa.String(length=50)), nullable=True),
    sa.Column('position', sa.Integer(), server_default='0', nullable=False),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("academic_year IS NULL OR academic_year ~ '^[0-9]{4}-[0-9]{4}$'", name=op.f('ck_admission_conditions_academic_year_format')),
    sa.CheckConstraint('minimum_average IS NULL OR minimum_average BETWEEN 0 AND 20', name=op.f('ck_admission_conditions_average_range')),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_admission_conditions_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_admission_conditions_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admission_conditions')),
    sa.UniqueConstraint('program_id', 'academic_year', 'position', name=op.f('uq_admission_conditions_program_id_academic_year_position'))
    )
    op.create_index(op.f('ix_admission_conditions_program_id'), 'admission_conditions', ['program_id'], unique=False)
    op.create_index(op.f('ix_admission_conditions_source_document_id'), 'admission_conditions', ['source_document_id'], unique=False)
    op.create_table('career_outcomes',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('sector', sa.String(length=100), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_career_outcomes_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_career_outcomes_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_career_outcomes')),
    sa.UniqueConstraint('program_id', 'title', name=op.f('uq_career_outcomes_program_id_title'))
    )
    op.create_index(op.f('ix_career_outcomes_program_id'), 'career_outcomes', ['program_id'], unique=False)
    op.create_index(op.f('ix_career_outcomes_source_document_id'), 'career_outcomes', ['source_document_id'], unique=False)
    op.create_table('consents',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=True),
    sa.Column('conversation_id', sa.BigInteger(), nullable=True),
    sa.Column('consent_type', postgresql.ENUM('data_processing', 'ai_processing', 'audio_recording', 'email_notifications', name='consent_type', create_type=False), nullable=False),
    sa.Column('policy_version', sa.String(length=20), nullable=False),
    sa.Column('granted', sa.Boolean(), nullable=False),
    sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('revoked_at IS NULL OR revoked_at >= granted_at', name=op.f('ck_consents_revocation_after_grant')),
    sa.CheckConstraint('user_id IS NOT NULL OR conversation_id IS NOT NULL', name=op.f('ck_consents_has_subject')),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_consents_conversation_id_conversations'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_consents_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_consents'))
    )
    op.create_index(op.f('ix_consents_conversation_id'), 'consents', ['conversation_id'], unique=False)
    op.create_index('ix_consents_user_type', 'consents', ['user_id', 'consent_type'], unique=False)
    op.create_table('document_chunks',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=True),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('section_title', sa.String(length=255), nullable=True),
    sa.Column('page_number', sa.Integer(), nullable=True),
    sa.Column('token_count', sa.Integer(), nullable=True),
    sa.Column('embedding', Vector(1024), nullable=True),
    sa.Column('embedding_model', sa.String(length=100), nullable=True),
    sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('chunk_index >= 0', name=op.f('ck_document_chunks_chunk_index_positive')),
    sa.CheckConstraint('token_count IS NULL OR token_count > 0', name=op.f('ck_document_chunks_token_count_positive')),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_document_chunks_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_document_chunks_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document_chunks')),
    sa.UniqueConstraint('source_document_id', 'chunk_index', name=op.f('uq_document_chunks_source_document_id_chunk_index'))
    )
    op.create_index('ix_document_chunks_embedding_hnsw', 'document_chunks', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index(op.f('ix_document_chunks_program_id'), 'document_chunks', ['program_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_source_document_id'), 'document_chunks', ['source_document_id'], unique=False)
    op.create_table('dossiers',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('candidate_id', sa.BigInteger(), nullable=False),
    sa.Column('campaign_id', sa.BigInteger(), nullable=False),
    sa.Column('status', postgresql.ENUM('open', 'in_progress', 'interview_scheduled', 'decision_pending', 'decided', 'enrolled', 'withdrawn', 'closed', name='dossier_status', create_type=False), server_default='open', nullable=False),
    sa.Column('ai_summary', sa.Text(), nullable=True),
    sa.Column('ai_summary_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('(ai_summary IS NULL) = (ai_summary_updated_at IS NULL)', name=op.f('ck_dossiers_ai_summary_has_date')),
    sa.ForeignKeyConstraint(['campaign_id'], ['admission_campaigns.id'], name=op.f('fk_dossiers_campaign_id_admission_campaigns'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_dossiers_candidate_id_candidates'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_dossiers'))
    )
    op.create_index('ix_dossiers_campaign_status', 'dossiers', ['campaign_id', 'status'], unique=False)
    op.create_index(op.f('ix_dossiers_candidate_id'), 'dossiers', ['candidate_id'], unique=False)
    op.create_index('uq_dossiers_active_candidate_campaign', 'dossiers', ['candidate_id', 'campaign_id'], unique=True, postgresql_where=sa.text("status NOT IN ('enrolled', 'withdrawn', 'closed')"))
    op.create_table('messages',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('conversation_id', sa.BigInteger(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('sender', postgresql.ENUM('user', 'assistant', 'system', name='message_sender', create_type=False), nullable=False),
    sa.Column('channel', postgresql.ENUM('text', 'audio', name='message_channel', create_type=False), server_default='text', nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('detected_language', postgresql.ENUM('fr', 'ar', 'tn_darija', 'arabizi', 'en', 'mixed', 'unknown', name='message_language', create_type=False), server_default='unknown', nullable=False),
    sa.Column('language_confidence', sa.Numeric(precision=3, scale=2), nullable=True),
    sa.Column('audio_uri', sa.String(length=1024), nullable=True),
    sa.Column('audio_duration_ms', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("channel <> 'audio' OR audio_uri IS NOT NULL", name=op.f('ck_messages_audio_has_uri')),
    sa.CheckConstraint('language_confidence IS NULL OR language_confidence BETWEEN 0 AND 1', name=op.f('ck_messages_confidence_range')),
    sa.CheckConstraint('sequence >= 1', name=op.f('ck_messages_sequence_positive')),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_messages_conversation_id_conversations'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_messages')),
    sa.UniqueConstraint('conversation_id', 'sequence', name=op.f('uq_messages_conversation_id_sequence'))
    )
    op.create_table('program_pathways',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('from_program_id', sa.BigInteger(), nullable=False),
    sa.Column('to_program_id', sa.BigInteger(), nullable=False),
    sa.Column('entry_level', sa.String(length=100), nullable=True),
    sa.Column('conditions', sa.Text(), nullable=True),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('from_program_id <> to_program_id', name=op.f('ck_program_pathways_distinct_programs')),
    sa.ForeignKeyConstraint(['from_program_id'], ['programs.id'], name=op.f('fk_program_pathways_from_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_program_pathways_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['to_program_id'], ['programs.id'], name=op.f('fk_program_pathways_to_program_id_programs'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program_pathways')),
    sa.UniqueConstraint('from_program_id', 'to_program_id', name=op.f('uq_program_pathways_from_program_id_to_program_id'))
    )
    op.create_index(op.f('ix_program_pathways_from_program_id'), 'program_pathways', ['from_program_id'], unique=False)
    op.create_index(op.f('ix_program_pathways_source_document_id'), 'program_pathways', ['source_document_id'], unique=False)
    op.create_index(op.f('ix_program_pathways_to_program_id'), 'program_pathways', ['to_program_id'], unique=False)
    op.create_table('program_prerequisites',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=False),
    sa.Column('kind', postgresql.ENUM('diploma', 'level', 'subject', 'skill', name='prerequisite_kind', create_type=False), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_mandatory', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('position', sa.Integer(), server_default='0', nullable=False),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_program_prerequisites_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_program_prerequisites_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_program_prerequisites')),
    sa.UniqueConstraint('program_id', 'label', name=op.f('uq_program_prerequisites_program_id_label'))
    )
    op.create_index(op.f('ix_program_prerequisites_program_id'), 'program_prerequisites', ['program_id'], unique=False)
    op.create_index(op.f('ix_program_prerequisites_source_document_id'), 'program_prerequisites', ['source_document_id'], unique=False)
    op.create_table('recommendations',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('candidate_id', sa.BigInteger(), nullable=True),
    sa.Column('conversation_id', sa.BigInteger(), nullable=True),
    sa.Column('program_id', sa.BigInteger(), nullable=False),
    sa.Column('rank', sa.SmallInteger(), nullable=False),
    sa.Column('compatibility_score', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('justification', sa.Text(), nullable=False),
    sa.Column('cited_sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('model_name', sa.String(length=100), nullable=True),
    sa.Column('review_status', postgresql.ENUM('pending', 'confirmed', 'adjusted', name='review_status', create_type=False), server_default='pending', nullable=False),
    sa.Column('reviewed_by', sa.BigInteger(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("(review_status = 'pending' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR (review_status <> 'pending' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)", name=op.f('ck_recommendations_review_consistency')),
    sa.CheckConstraint("review_status <> 'adjusted' OR review_comment IS NOT NULL", name=op.f('ck_recommendations_adjusted_has_comment')),
    sa.CheckConstraint('candidate_id IS NOT NULL OR conversation_id IS NOT NULL', name=op.f('ck_recommendations_has_subject')),
    sa.CheckConstraint('compatibility_score BETWEEN 0 AND 100', name=op.f('ck_recommendations_score_range')),
    sa.CheckConstraint('rank BETWEEN 1 AND 3', name=op.f('ck_recommendations_rank_range')),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_recommendations_candidate_id_candidates'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], name=op.f('fk_recommendations_conversation_id_conversations'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_recommendations_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], name=op.f('fk_recommendations_reviewed_by_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recommendations'))
    )
    op.create_index(op.f('ix_recommendations_candidate_id'), 'recommendations', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_recommendations_conversation_id'), 'recommendations', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_recommendations_program_id'), 'recommendations', ['program_id'], unique=False)
    op.create_index('ix_recommendations_review_status', 'recommendations', ['review_status'], unique=False)
    op.create_table('sync_logs',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('sync_job_id', sa.BigInteger(), nullable=False),
    sa.Column('level', postgresql.ENUM('info', 'warning', 'error', name='sync_log_level', create_type=False), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['sync_job_id'], ['sync_jobs.id'], name=op.f('fk_sync_logs_sync_job_id_sync_jobs'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sync_logs'))
    )
    op.create_index(op.f('ix_sync_logs_sync_job_id'), 'sync_logs', ['sync_job_id'], unique=False)
    op.create_table('tuition_fees',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=False),
    sa.Column('academic_year', sa.String(length=9), nullable=False),
    sa.Column('fee_type', postgresql.ENUM('registration', 'tuition', 'exam', 'other', name='fee_type', create_type=False), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=3), nullable=False),
    sa.Column('currency', sa.String(length=3), server_default='TND', nullable=False),
    sa.Column('payment_terms', sa.Text(), nullable=True),
    sa.Column('source_document_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("academic_year ~ '^[0-9]{4}-[0-9]{4}$'", name=op.f('ck_tuition_fees_academic_year_format')),
    sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f('ck_tuition_fees_currency_iso4217')),
    sa.CheckConstraint('amount >= 0', name=op.f('ck_tuition_fees_amount_positive')),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_tuition_fees_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['source_document_id'], ['source_documents.id'], name=op.f('fk_tuition_fees_source_document_id_source_documents'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tuition_fees')),
    sa.UniqueConstraint('program_id', 'academic_year', 'fee_type', name=op.f('uq_tuition_fees_program_id_academic_year_fee_type'))
    )
    op.create_index('ix_tuition_fees_program_year', 'tuition_fees', ['program_id', 'academic_year'], unique=False)
    op.create_index(op.f('ix_tuition_fees_source_document_id'), 'tuition_fees', ['source_document_id'], unique=False)
    op.create_table('appointments',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('dossier_id', sa.BigInteger(), nullable=False),
    sa.Column('organizer_id', sa.BigInteger(), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('duration_minutes', sa.SmallInteger(), server_default='30', nullable=False),
    sa.Column('mode', postgresql.ENUM('on_site', 'online', 'phone', name='appointment_mode', create_type=False), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('meeting_url', sa.String(length=1024), nullable=True),
    sa.Column('status', postgresql.ENUM('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show', name='appointment_status', create_type=False), server_default='scheduled', nullable=False),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("mode <> 'online' OR meeting_url IS NOT NULL", name=op.f('ck_appointments_online_has_url')),
    sa.CheckConstraint("status <> 'cancelled' OR cancellation_reason IS NOT NULL", name=op.f('ck_appointments_cancel_has_reason')),
    sa.CheckConstraint('duration_minutes BETWEEN 5 AND 240', name=op.f('ck_appointments_duration_range')),
    sa.ForeignKeyConstraint(['dossier_id'], ['dossiers.id'], name=op.f('fk_appointments_dossier_id_dossiers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['organizer_id'], ['users.id'], name=op.f('fk_appointments_organizer_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_appointments'))
    )
    op.create_index(op.f('ix_appointments_dossier_id'), 'appointments', ['dossier_id'], unique=False)
    op.create_index('ix_appointments_organizer_scheduled', 'appointments', ['organizer_id', 'scheduled_at'], unique=False)
    op.create_table('decisions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('dossier_id', sa.BigInteger(), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=True),
    sa.Column('decision', postgresql.ENUM('admitted', 'admitted_with_conditions', 'waitlisted', 'rejected', name='decision_value', create_type=False), nullable=False),
    sa.Column('observations', sa.Text(), nullable=True),
    sa.Column('responsible_id', sa.BigInteger(), nullable=False),
    sa.Column('decided_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("decision <> 'admitted_with_conditions' OR observations IS NOT NULL", name=op.f('ck_decisions_conditions_explained')),
    sa.CheckConstraint("decision NOT IN ('admitted', 'admitted_with_conditions') OR program_id IS NOT NULL", name=op.f('ck_decisions_admission_has_program')),
    sa.ForeignKeyConstraint(['dossier_id'], ['dossiers.id'], name=op.f('fk_decisions_dossier_id_dossiers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_decisions_program_id_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['responsible_id'], ['users.id'], name=op.f('fk_decisions_responsible_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_decisions'))
    )
    op.create_index(op.f('ix_decisions_dossier_id'), 'decisions', ['dossier_id'], unique=False)
    op.create_index(op.f('ix_decisions_program_id'), 'decisions', ['program_id'], unique=False)
    op.create_index(op.f('ix_decisions_responsible_id'), 'decisions', ['responsible_id'], unique=False)
    op.create_table('equivalence_requests',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('dossier_id', sa.BigInteger(), nullable=False),
    sa.Column('target_program_id', sa.BigInteger(), nullable=False),
    sa.Column('origin_diploma', sa.String(length=255), nullable=False),
    sa.Column('origin_program', sa.String(length=255), nullable=True),
    sa.Column('origin_institution', sa.String(length=255), nullable=False),
    sa.Column('origin_country', sa.String(length=2), server_default='TN', nullable=False),
    sa.Column('origin_level', postgresql.ENUM('lycee', 'bac', 'bac_plus_1', 'bac_plus_2', 'bac_plus_3', 'bac_plus_4_or_more', 'other', name='education_level', create_type=False), nullable=True),
    sa.Column('requested_entry_level', sa.String(length=100), nullable=True),
    sa.Column('status', postgresql.ENUM('submitted', 'under_review', 'accepted', 'rejected', 'more_info_requested', name='equivalence_status', create_type=False), server_default='submitted', nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('reviewed_by', sa.BigInteger(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_comment', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("status NOT IN ('accepted', 'rejected', 'more_info_requested') OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)", name=op.f('ck_equivalence_requests_reviewed_when_decided')),
    sa.ForeignKeyConstraint(['dossier_id'], ['dossiers.id'], name=op.f('fk_equivalence_requests_dossier_id_dossiers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], name=op.f('fk_equivalence_requests_reviewed_by_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['target_program_id'], ['programs.id'], name=op.f('fk_equivalence_requests_target_program_id_programs'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_equivalence_requests'))
    )
    op.create_index(op.f('ix_equivalence_requests_dossier_id'), 'equivalence_requests', ['dossier_id'], unique=False)
    op.create_index('ix_equivalence_requests_status', 'equivalence_requests', ['status'], unique=False)
    op.create_index(op.f('ix_equivalence_requests_target_program_id'), 'equivalence_requests', ['target_program_id'], unique=False)
    op.create_table('notifications',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('dossier_id', sa.BigInteger(), nullable=True),
    sa.Column('kind', postgresql.ENUM('reminder', 'confirmation', 'appointment', 'decision', 'other', name='notification_kind', create_type=False), nullable=False),
    sa.Column('channel', postgresql.ENUM('email', 'in_app', name='notification_channel', create_type=False), server_default='email', nullable=False),
    sa.Column('template_code', sa.String(length=100), nullable=True),
    sa.Column('subject', sa.String(length=255), nullable=False),
    sa.Column('scheduled_for', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('status', postgresql.ENUM('pending', 'sent', 'failed', 'cancelled', name='notification_status', create_type=False), server_default='pending', nullable=False),
    sa.Column('attempts', sa.SmallInteger(), server_default='0', nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("status <> 'sent' OR sent_at IS NOT NULL", name=op.f('ck_notifications_sent_has_date')),
    sa.CheckConstraint('attempts >= 0', name=op.f('ck_notifications_attempts_positive')),
    sa.ForeignKeyConstraint(['dossier_id'], ['dossiers.id'], name=op.f('fk_notifications_dossier_id_dossiers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index(op.f('ix_notifications_dossier_id'), 'notifications', ['dossier_id'], unique=False)
    op.create_index('ix_notifications_status_scheduled', 'notifications', ['status', 'scheduled_for'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_table('preinscriptions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('dossier_id', sa.BigInteger(), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=False),
    sa.Column('status', postgresql.ENUM('draft', 'submitted', 'under_review', 'validated', 'rejected', 'cancelled', name='preinscription_status', create_type=False), server_default='draft', nullable=False),
    sa.Column('choice_rank', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("status = 'draft' OR submitted_at IS NOT NULL", name=op.f('ck_preinscriptions_submitted_has_date')),
    sa.ForeignKeyConstraint(['dossier_id'], ['dossiers.id'], name=op.f('fk_preinscriptions_dossier_id_dossiers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_preinscriptions_program_id_programs'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_preinscriptions')),
    sa.UniqueConstraint('dossier_id', 'program_id', name=op.f('uq_preinscriptions_dossier_id_program_id'))
    )
    op.create_index(op.f('ix_preinscriptions_dossier_id'), 'preinscriptions', ['dossier_id'], unique=False)
    op.create_index(op.f('ix_preinscriptions_program_id'), 'preinscriptions', ['program_id'], unique=False)
    op.create_index('ix_preinscriptions_status', 'preinscriptions', ['status'], unique=False)
    op.create_table('qcm',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('dossier_id', sa.BigInteger(), nullable=False),
    sa.Column('program_id', sa.BigInteger(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('generated_by', postgresql.ENUM('ai', 'template', name='qcm_generated_by', create_type=False), nullable=False),
    sa.Column('template_code', sa.String(length=100), nullable=True),
    sa.Column('model_name', sa.String(length=100), nullable=True),
    sa.Column('status', postgresql.ENUM('generated', 'in_progress', 'completed', 'expired', name='qcm_status', create_type=False), server_default='generated', nullable=False),
    sa.Column('score', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('max_score', sa.Numeric(precision=6, scale=2), nullable=False),
    sa.Column('summary_for_interviewer', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("generated_by <> 'template' OR template_code IS NOT NULL", name=op.f('ck_qcm_template_has_code')),
    sa.CheckConstraint("status <> 'completed' OR (score IS NOT NULL AND completed_at IS NOT NULL)", name=op.f('ck_qcm_completed_has_score')),
    sa.CheckConstraint('max_score > 0', name=op.f('ck_qcm_max_score_positive')),
    sa.CheckConstraint('score IS NULL OR (score >= 0 AND score <= max_score)', name=op.f('ck_qcm_score_range')),
    sa.ForeignKeyConstraint(['dossier_id'], ['dossiers.id'], name=op.f('fk_qcm_dossier_id_dossiers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name=op.f('fk_qcm_program_id_programs'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qcm'))
    )
    op.create_index(op.f('ix_qcm_dossier_id'), 'qcm', ['dossier_id'], unique=False)
    op.create_index(op.f('ix_qcm_program_id'), 'qcm', ['program_id'], unique=False)
    op.create_table('equivalence_documents',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('equivalence_request_id', sa.BigInteger(), nullable=False),
    sa.Column('document_type', postgresql.ENUM('diploma', 'transcript', 'syllabus', 'identity', 'other', name='equivalence_document_type', create_type=False), nullable=False),
    sa.Column('file_name', sa.String(length=255), nullable=False),
    sa.Column('storage_key', sa.String(length=1024), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name=op.f('ck_equivalence_documents_sha256_format')),
    sa.CheckConstraint('size_bytes > 0', name=op.f('ck_equivalence_documents_size_positive')),
    sa.ForeignKeyConstraint(['equivalence_request_id'], ['equivalence_requests.id'], name=op.f('fk_equivalence_documents_equivalence_request_id_equivalence_requests'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_equivalence_documents')),
    sa.UniqueConstraint('storage_key', name=op.f('uq_equivalence_documents_storage_key'))
    )
    op.create_index(op.f('ix_equivalence_documents_equivalence_request_id'), 'equivalence_documents', ['equivalence_request_id'], unique=False)
    op.create_table('interview_results',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('appointment_id', sa.BigInteger(), nullable=False),
    sa.Column('interviewer_id', sa.BigInteger(), nullable=False),
    sa.Column('observations', sa.Text(), nullable=False),
    sa.Column('score', sa.Numeric(precision=4, scale=2), nullable=True),
    sa.Column('opinion', postgresql.ENUM('favorable', 'reserved', 'unfavorable', name='interview_opinion', create_type=False), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('score IS NULL OR score BETWEEN 0 AND 20', name=op.f('ck_interview_results_score_range')),
    sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], name=op.f('fk_interview_results_appointment_id_appointments'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['interviewer_id'], ['users.id'], name=op.f('fk_interview_results_interviewer_id_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_interview_results')),
    sa.UniqueConstraint('appointment_id', name=op.f('uq_interview_results_appointment_id'))
    )
    op.create_index(op.f('ix_interview_results_interviewer_id'), 'interview_results', ['interviewer_id'], unique=False)
    op.create_table('qcm_questions',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('qcm_id', sa.BigInteger(), nullable=False),
    sa.Column('position', sa.SmallInteger(), nullable=False),
    sa.Column('topic', sa.String(length=100), nullable=True),
    sa.Column('question_text', sa.Text(), nullable=False),
    sa.Column('choices', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('correct_choice_index', sa.SmallInteger(), nullable=False),
    sa.Column('points', sa.Numeric(precision=5, scale=2), server_default='1', nullable=False),
    sa.Column('explanation', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("jsonb_typeof(choices) = 'array' AND jsonb_array_length(choices) >= 2", name=op.f('ck_qcm_questions_choices_array')),
    sa.CheckConstraint('correct_choice_index >= 0 AND correct_choice_index < jsonb_array_length(choices)', name=op.f('ck_qcm_questions_correct_choice_in_range')),
    sa.CheckConstraint('points > 0', name=op.f('ck_qcm_questions_points_positive')),
    sa.ForeignKeyConstraint(['qcm_id'], ['qcm.id'], name=op.f('fk_qcm_questions_qcm_id_qcm'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qcm_questions')),
    sa.UniqueConstraint('qcm_id', 'position', name=op.f('uq_qcm_questions_qcm_id_position'))
    )
    op.create_table('qcm_answers',
    sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('question_id', sa.BigInteger(), nullable=False),
    sa.Column('selected_choice_index', sa.SmallInteger(), nullable=False),
    sa.Column('is_correct', sa.Boolean(), nullable=False),
    sa.Column('points_awarded', sa.Numeric(precision=5, scale=2), server_default='0', nullable=False),
    sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint('points_awarded >= 0', name=op.f('ck_qcm_answers_points_positive')),
    sa.ForeignKeyConstraint(['question_id'], ['qcm_questions.id'], name=op.f('fk_qcm_answers_question_id_qcm_questions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qcm_answers')),
    sa.UniqueConstraint('question_id', name=op.f('uq_qcm_answers_question_id'))
    )

    _create_triggers()


def downgrade() -> None:
    # Les triggers disparaissent avec leurs tables ; l'extension vector est conservée.
    for table in reversed(TABLES):
        op.drop_table(table)
    for fn in FUNCTION_NAMES:
        op.execute(f"DROP FUNCTION IF EXISTS {fn}")
    bind = op.get_bind()
    for name in ENUMS:
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
