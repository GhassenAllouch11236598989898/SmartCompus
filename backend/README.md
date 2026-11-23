# SmartCampus AI — Backend (epic SA-10 : données, base PostgreSQL et API catalogue)

FastAPI + PostgreSQL/pgvector. Ce dépôt couvre le **modèle de données complet** (catalogue, candidatures, documents RAG), la **base PostgreSQL** (rôles à moindre privilège, migrations, données de démo) et l'**API catalogue** (formations, tarifs, conditions d'admission, comparaison).

> Hors périmètre de cet epic : `/auth/*`, `/me`, `/chat/*`, `/equivalences`, `/preinscriptions`, `/qcm/*`, `/rendez-vous`, `/dossiers/me`, `/responsable/*`, agents LangGraph, pipeline RAG, STT/TTS, emails. Les tables correspondantes existent déjà.

## 1. Démarrage (une commande)

Prérequis : Docker Desktop (avec quelques Go libres sur le disque qui héberge Docker).

```powershell
cd backend
copy .env.example .env        # puis changer les mots de passe et JWT_SECRET_KEY
docker compose up -d --build
```

Au démarrage, le conteneur `api` exécute `alembic upgrade head` puis le seed DEMO (idempotent), et lance uvicorn.

| URL | |
|---|---|
| http://localhost:8000/docs | Swagger (OpenAPI) |
| http://localhost:8000/api/v1/health/ready | API + base |
| `localhost:5434` | PostgreSQL (port hôte configurable : `POSTGRES_HOST_PORT`) |

Obtenir un JWT de développement (l'émission réelle viendra de l'epic Auth) :

```powershell
docker compose exec api python -m scripts.issue_token admin@demo.smartcampus.invalid
```

Les comptes de démo sont listés dans [SEED_DATA_NOTES.md](SEED_DATA_NOTES.md) (mot de passe `Demo2026!`). La collection de requêtes est dans [requests/catalogue.http](requests/catalogue.http).

## 2. Variables d'environnement

Toutes sont décrites dans [.env.example](.env.example). Les principales :

| Variable | Rôle |
|---|---|
| `POSTGRES_SUPERUSER`, `POSTGRES_SUPERUSER_PASSWORD` | superuser, utilisé **uniquement** par le script d'initialisation |
| `SMARTCAMPUS_OWNER_PASSWORD` | rôle `smartcampus_owner` : migrations et seed |
| `SMARTCAMPUS_APP_PASSWORD` | rôle `smartcampus_app` : API (SELECT, INSERT, UPDATE, **sans DELETE ni DDL**) |
| `AI_READONLY_PASSWORD` | rôle `ai_readonly` : outil SQL de l'agent IA (vues `ai_views` seulement) |
| `JWT_SECRET_KEY` | secret HS256 (≥ 32 caractères aléatoires) |
| `CORS_ORIGINS` | origines du frontend Next.js |
| `RUN_MIGRATIONS`, `RUN_SEED` | migrations et seed au démarrage du conteneur |
| `DATABASE_URL`, `MIGRATION_DATABASE_URL`, `AI_READONLY_DATABASE_URL`, `TEST_*` | URLs pour exécuter hors Docker (depuis l'hôte) |

> Le script `docker/postgres/init/01-roles-and-databases.sh` ne s'exécute que sur un **volume vide**. Après un changement de mot de passe : `docker compose down -v` (⚠️ efface les données locales).

## 3. Commandes utiles

```powershell
# Migrations (dans le conteneur ou depuis l'hôte avec le venv)
docker compose exec api alembic upgrade head
docker compose exec api alembic downgrade base
docker compose exec api alembic upgrade head --sql      # SQL généré, sans base

# Seed DEMO (relançable sans doublons)
docker compose exec api python -m seeds.seed

# Régénérer l'ERD et le dictionnaire de données depuis les modèles
docker compose exec api python -m scripts.gen_docs
```

## 4. Tests

Les tests utilisent une **vraie base** `smartcampus_test`, créée par le script d'init. Le `conftest` y joue downgrade → upgrade → downgrade → upgrade, puis lance le seed deux fois pour vérifier l'idempotence. Chaque test tourne dans une transaction annulée, avec le rôle applicatif.

```powershell
# Dans le conteneur
docker compose exec api pytest --cov=app --cov-report=term-missing

# Ou depuis l'hôte (Postgres du compose démarré)
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

La couverture minimale est fixée à 80 % dans `.coveragerc`.

## 5. API catalogue (préfixe `/api/v1`)

| Méthode | Route | Accès |
|---|---|---|
| GET | `/formations` | public (publiées). Filtres : `etablissement`, `type_parcours`, `duree_min`, `duree_max`, `statut`*, `q`, `tri`, `page`, `taille` |
| GET | `/formations/{id}` | public (publiées) ; brouillons visibles dans le périmètre |
| GET | `/formations/{id}/tarifs?annee_academique=2026-2027` | public |
| GET | `/formations/{id}/conditions-admission?annee_academique=…` | public |
| GET | `/formations/comparer?ids=1,2,3` | public (2 à 3 formations) |
| POST | `/formations` | admin, responsable de l'établissement |
| PUT / PATCH | `/formations/{id}` | admin, responsable de l'établissement |
| POST | `/formations/{id}/archiver` | admin, responsable de l'établissement |

\* `statut` ≠ `published` est réservé aux rôles de gestion.

Conventions :
- routes et paramètres de requête en français, champs JSON en anglais `snake_case` ;
- montants en chaîne décimale (`"7500.000"`) ;
- **chaque information renvoie `source` (document, type, version, date) et `updated_at`** ;
- pas de DELETE : une formation s'archive (405 sur DELETE) ;
- erreurs au format `{"error": {"code", "message", "details"}}` ;
- en-tête `X-Response-Time-ms` sur chaque réponse.

## 6. Structure

```text
backend/
├── app/
│   ├── core/            config, database (engines), security (bcrypt/JWT), errors, ai_sql (garde-fou SQL IA)
│   ├── models/          SQLAlchemy : catalog (SA-12), identity + applications (SA-13), documents (SA-14)
│   ├── schemas/         Pydantic v2 (pagination, sources, formations/tarifs/conditions)
│   ├── repositories/    requêtes SQL (programs, dossier_scope = périmètre des responsables)
│   ├── services/        règles métier (visibilité, RBAC par établissement, archivage, audit)
│   └── api/             deps (JWT/RBAC) + v1/endpoints (health, formations)
├── alembic/versions/    0001 schéma + triggers, 0002 vues ai_views + privilèges
├── seeds/seed.py        données DEMO idempotentes
├── docker/              init Postgres (rôles, bases, pgvector) + entrypoint API
├── docs/                erd.md, data_dictionary.md, normalisation.md, security.md, backlog_suggestions.md
├── requests/            collection .http
├── scripts/             gen_docs, issue_token, print_ddl
├── tests/               pytest (migrations, seed, règles DB, ai_readonly, périmètre, API, plateforme)
├── docker-compose.yml, Dockerfile, .env.example, SEED_DATA_NOTES.md
```

## 7. Documentation

- [docs/erd.md](docs/erd.md) : diagrammes Mermaid (générés)
- [docs/data_dictionary.md](docs/data_dictionary.md) : dictionnaire de données (généré)
- [docs/normalisation.md](docs/normalisation.md) : normalisation et règles en base
- [docs/security.md](docs/security.md) : rôles PostgreSQL, outil SQL de l'IA, données personnelles
- [SEED_DATA_NOTES.md](SEED_DATA_NOTES.md) : **données fictives à remplacer**
- [docs/backlog_suggestions.md](docs/backlog_suggestions.md) : idées hors sprint
