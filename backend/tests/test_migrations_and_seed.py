"""SA-17 / SA-18 — migrations reproductibles et seed idempotent."""

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Candidate,
    Conversation,
    Decision,
    DocumentChunk,
    EquivalenceRequest,
    Institution,
    Message,
    Program,
    Qcm,
    Recommendation,
    SourceDocument,
    User,
)


def test_downgrade_base_removes_all_tables(migration_report):
    assert migration_report["tables_after_downgrade"] == 0


def test_upgrade_creates_all_tables_views_and_extension(owner_db: Session):
    tables = set(owner_db.scalars(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
    )))
    assert set(Base.metadata.tables) <= tables
    views = set(owner_db.scalars(text("SELECT table_name FROM information_schema.views WHERE table_schema='ai_views'")))
    assert {"v_formations_public", "v_candidate_dossier_summary", "v_tuition_fees_public"} <= views
    assert owner_db.scalar(text("SELECT count(*) FROM pg_extension WHERE extname='vector'")) == 1
    version = owner_db.scalar(text("SELECT version_num FROM alembic_version"))
    assert version == "0003_conversation_memory"


def test_enums_and_key_indexes_exist(owner_db: Session):
    enums = set(owner_db.scalars(text("SELECT typname FROM pg_type WHERE typtype='e'")))
    assert {"program_status", "dossier_status", "equivalence_status", "review_status", "role_code"} <= enums
    indexes = set(owner_db.scalars(text("SELECT indexname FROM pg_indexes WHERE schemaname='public'")))
    assert {"ix_programs_search_vector", "uq_dossiers_active_candidate_campaign",
            "ix_document_chunks_embedding_hnsw", "ix_tuition_fees_program_year"} <= indexes


def test_seed_is_idempotent(migration_report):
    first, second = migration_report["counts_first"], migration_report["counts_second"]
    assert first == second
    assert sum(first.values()) > 100


def test_seed_minimum_content(db: Session):
    count = lambda model, *where: db.scalar(select(func.count()).select_from(model).where(*where))  # noqa: E731
    assert count(Institution) == 2
    assert count(Program, Program.status == "published") >= 5
    assert count(User) >= 10
    assert count(Candidate) >= 5
    assert count(Conversation, Conversation.candidate_id.is_(None)) == 1
    langs = set(db.scalars(select(Message.detected_language).distinct()))
    assert {"fr", "tn_darija", "arabizi"} <= {lang.value for lang in langs}
    assert count(EquivalenceRequest) >= 1
    assert count(Qcm) >= 1
    assert count(Decision) >= 1
    assert count(Recommendation, Recommendation.review_status == "pending") >= 1
    assert count(DocumentChunk, DocumentChunk.embedding.is_not(None)) >= 5


def test_all_seed_data_is_marked_demo(db: Session):
    assert db.scalar(select(func.count()).select_from(Program).where(Program.is_demo.is_(False))) == 0
    assert db.scalar(select(func.count()).select_from(User).where(User.is_demo.is_(False))) == 0
    assert set(db.scalars(select(SourceDocument.version).distinct())) == {"DEMO"}


def test_one_user_per_role(db: Session):
    rows = db.execute(text(
        "SELECT r.code::text, count(*) FROM roles r JOIN user_roles ur ON ur.role_id = r.id GROUP BY r.code"
    )).all()
    per_role = dict(rows)
    assert set(per_role) == {"candidate", "responsable_iit", "responsable_isb", "responsable_entretien",
                             "direction", "admin"}
    assert all(per_role[r] == 1 for r in per_role if r != "candidate")


def test_ai_views_summary_hides_identity(db: Session, owner_db: Session):
    cols = set(owner_db.scalars(text(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='ai_views' "
        "AND table_name='v_candidate_dossier_summary'"
    )))
    assert not cols & {"email", "first_name", "last_name", "phone", "password_hash", "session_token_hash"}
