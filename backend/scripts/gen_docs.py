"""Génère docs/erd.md (Mermaid) et docs/data_dictionary.md à partir des modèles SQLAlchemy.

Usage : python -m scripts.gen_docs
La documentation reste ainsi synchronisée avec le schéma réel (source de vérité = modèles + migration).
"""

import inspect
from pathlib import Path

from sqlalchemy import CheckConstraint, Enum, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.models import Base

DOCS = Path(__file__).resolve().parent.parent / "docs"

DOMAINS: dict[str, list[str]] = {
    "SA-12 — Catalogue académique": [
        "institutions", "program_types", "programs", "program_prerequisites", "admission_conditions",
        "career_outcomes", "program_pathways", "tuition_fees", "admission_campaigns", "source_documents",
    ],
    "SA-13 — Utilisateurs et candidatures": [
        "users", "roles", "user_roles", "candidates", "candidate_profiles", "conversations", "messages",
        "recommendations", "consents", "dossiers", "preinscriptions", "equivalence_requests",
        "equivalence_documents", "qcm", "qcm_questions", "qcm_answers", "appointments", "interview_results",
        "decisions", "notifications", "audit_log", "status_history",
    ],
    "SA-14 — Documents et synchronisation": [
        "source_documents", "document_chunks", "sync_jobs", "sync_logs",
    ],
}

COMMON_COLUMNS = {
    "id": "Clé primaire technique (BIGINT identity).",
    "created_at": "Date de création (UTC, défaut now()).",
    "updated_at": "Date de dernière modification (trigger set_updated_at).",
    "is_demo": "true = donnée FICTIVE de démonstration, à remplacer (voir SEED_DATA_NOTES.md).",
    "source_document_id": "Document source officiel de l'information (traçabilité obligatoire).",
}

COLUMN_NOTES = {
    ("programs", "description"): "Contenu de la formation.",
    ("programs", "duration_semesters"): "Durée en semestres (1–12).",
    ("programs", "search_vector"): "tsvector français généré (titre + résumé + description), index GIN.",
    ("programs", "status"): "draft / published / archived. Seules les formations published sont publiques.",
    ("admission_conditions", "academic_year"): "NULL = valable pour toutes les années.",
    ("admission_conditions", "minimum_average"): "Moyenne minimale sur 20.",
    ("tuition_fees", "amount"): "Montant (NUMERIC 12,3 : le dinar compte 3 décimales).",
    ("tuition_fees", "currency"): "Code ISO 4217 (TND par défaut).",
    ("roles", "institution_id"): "Périmètre du rôle (IIT/ISB) ; NULL = transverse.",
    ("users", "password_hash"): "Hash bcrypt/argon2 uniquement (CHECK). NULL pour un compte technique.",
    ("users", "is_service_account"): "Compte technique (agent IA) : interdit de décision.",
    ("candidates", "birth_year"): "Année de naissance seule (minimisation).",
    ("conversations", "candidate_id"): "NULL pour un visiteur anonyme ; renseigné à la création du compte.",
    ("conversations", "session_token_hash"): "SHA-256 du jeton de session (jamais le jeton brut).",
    ("messages", "detected_language"): "fr, ar, tn_darija, arabizi, en, mixed, unknown.",
    ("messages", "content"): "Texte saisi ou transcription Whisper.",
    ("recommendations", "review_status"): "pending / confirmed / adjusted (revue humaine obligatoire).",
    ("recommendations", "reviewed_by"): "Responsable humain (trigger assert_human_responsable).",
    ("dossiers", "ai_summary"): "Résumé généré par l'agent IA (indicatif, jamais une décision).",
    ("decisions", "responsible_id"): "Responsable HUMAIN obligatoire (trigger) : un agent IA ne peut pas décider.",
    ("qcm", "summary_for_interviewer"): "Synthèse destinée au responsable d'entretien.",
    ("status_history", "changed_by"): "Lu depuis SET LOCAL app.current_user_id ; NULL = système.",
    ("document_chunks", "embedding"): "vector(1024) pgvector, index HNSW cosinus.",
    ("document_chunks", "program_id"): "Formation concernée (NULL = chunk transverse).",
}


def _tables() -> dict[str, Table]:
    return dict(Base.metadata.tables)


def _class_doc(table_name: str) -> str:
    for mapper in Base.registry.mappers:
        if mapper.local_table.name == table_name:
            doc = inspect.getdoc(mapper.class_) or ""
            return " ".join(doc.split())
    return ""


def _sql_type(col) -> str:
    if isinstance(col.type, Enum):
        return f"ENUM {col.type.name}"
    return str(col.type.compile(dialect=postgresql.dialect()))


def _mermaid_type(col) -> str:
    t = _sql_type(col).split("(")[0].replace("ENUM ", "enum_").replace(" ", "_").replace("[]", "_array")
    return t.lower()


def _relation_line(table: Table, fk) -> str:
    child_col = fk.parent
    parent = fk.column.table.name
    is_unique = child_col.unique or any(
        isinstance(c, UniqueConstraint) and list(c.columns.keys()) == [child_col.name] for c in table.constraints
    )
    parent_side = "|o" if child_col.nullable else "||"
    child_side = "o|" if is_unique else "o{"
    return f'    {parent} {parent_side}--{child_side} {table.name} : "{child_col.name}"'


def build_erd() -> str:
    tables = _tables()
    out = [
        "# ERD — SmartCampus AI (SA-11)",
        "",
        "> Fichier généré par `python -m scripts.gen_docs` à partir des modèles SQLAlchemy. Ne pas éditer à la main.",
        "",
        "Légende : `||--o{` = 1..N obligatoire, `|o--o{` = 0..1 vers N (FK nullable), `||--o|` = 1..1 (FK unique).",
        "",
    ]
    for domain, names in DOMAINS.items():
        out += [f"## {domain}", "", "```mermaid", "erDiagram"]
        for name in names:
            t = tables[name]
            out.append(f"    {name} {{")
            for col in t.columns:
                key = "PK" if col.primary_key else ("FK" if col.foreign_keys else ("UK" if col.unique else ""))
                out.append(f"        {_mermaid_type(col)} {col.name} {key}".rstrip())
            out.append("    }")
        for name in names:
            for fk in sorted(tables[name].foreign_keys, key=lambda f: f.parent.name):
                out.append(_relation_line(tables[name], fk))
        out += ["```", ""]
    return "\n".join(out) + "\n"


def build_dictionary() -> str:
    tables = _tables()
    out = [
        "# Dictionnaire de données — SmartCampus AI",
        "",
        "> Généré par `python -m scripts.gen_docs` depuis les modèles. La justification de la",
        "> normalisation et les règles transverses sont dans [normalisation.md](normalisation.md).",
        "",
        "Colonnes communes : " + "; ".join(f"`{k}` — {v}" for k, v in COMMON_COLUMNS.items()),
        "",
    ]
    seen: set[str] = set()
    for domain, names in DOMAINS.items():
        out += [f"## {domain}", ""]
        for name in names:
            if name in seen:
                out += [f"### `{name}`", "", "_Voir section SA-12._", ""]
                continue
            seen.add(name)
            t = tables[name]
            out += [f"### `{name}`", ""]
            doc = _class_doc(name)
            if doc:
                out += [doc, ""]
            out += ["| Colonne | Type | Null | Défaut | Clé / référence | Description |", "|---|---|---|---|---|---|"]
            for col in t.columns:
                default = ""
                if col.server_default is not None and hasattr(col.server_default, "arg"):
                    arg = col.server_default.arg
                    default = str(getattr(arg, "text", arg))
                if col.computed is not None:
                    default = "GENERATED"
                keys = []
                if col.primary_key:
                    keys.append("PK")
                for fk in col.foreign_keys:
                    keys.append(f"FK → {fk.column.table.name}.{fk.column.name}")
                if col.unique:
                    keys.append("UNIQUE")
                desc = COLUMN_NOTES.get((name, col.name)) or COMMON_COLUMNS.get(col.name, "")
                null = "oui" if col.nullable else "non"
                out.append(
                    f"| `{col.name}` | {_sql_type(col)} | {null} | {default.replace('|', '/')} | {', '.join(keys)} | {desc} |"
                )
            constraints = []
            for c in sorted(t.constraints, key=lambda c: str(c.name)):
                if isinstance(c, UniqueConstraint) and len(c.columns) > 1:
                    constraints.append(f"- UNIQUE `{c.name}` ({', '.join(c.columns.keys())})")
                elif isinstance(c, CheckConstraint):
                    constraints.append(f"- CHECK `{c.name}` : `{c.sqltext}`")
            for ix in sorted(t.indexes, key=lambda i: str(i.name)):
                kind = "UNIQUE INDEX" if ix.unique else "INDEX"
                using = ix.dialect_options["postgresql"].get("using")
                where = ix.dialect_options["postgresql"].get("where")
                extra = (f" USING {using}" if using else "") + (f" WHERE {where}" if where is not None else "")
                constraints.append(f"- {kind} `{ix.name}` ({', '.join(c.name for c in ix.columns)}){extra}")
            if constraints:
                out += ["", "Contraintes et index :", "", *constraints]
            out.append("")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    (DOCS / "erd.md").write_text(build_erd(), encoding="utf-8")
    (DOCS / "data_dictionary.md").write_text(build_dictionary(), encoding="utf-8")
    print(f"docs générées : {len(Base.metadata.tables)} tables")
