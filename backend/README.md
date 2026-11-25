# SmartCampus AI — Backend (epic SA-10 : données, base PostgreSQL et API catalogue)

FastAPI + PostgreSQL 17/pgvector (`pgvector/pgvector:pg17`, configurable via `POSTGRES_IMAGE_TAG`). Ce dépôt couvre le **modèle de données complet** (catalogue, candidatures, documents RAG), la **base PostgreSQL** (rôles à moindre privilège, migrations, données de démo) et l'**API catalogue** (formations, tarifs, conditions d'admission, comparaison).

> Epic **SA-30** (sélection et intégration du LLM) : chatbot multi-tours `/chat/*` et banc d'évaluation des LLM, voir [section 6](#6-chatbot-llm-epic-sa-30).
>
> Hors périmètre : `/auth/*`, `/me`, `/equivalences`, `/preinscriptions`, `/qcm/*`, `/rendez-vous`, `/dossiers/me`, `/responsable/*`, agents LangGraph, pipeline RAG, STT/TTS, emails. Les tables correspondantes existent déjà.

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

## 6. Chatbot LLM (epic SA-30)

Le backend parle à un **LLM open-source** servi par un serveur OpenAI-compatible (Ollama, vLLM, TGI...).
Modèle retenu et justification : [docs/llm_selection.md](docs/llm_selection.md) ; banc de comparaison :
[evaluation/README.md](evaluation/README.md).

```powershell
ollama pull qwen2.5:7b-instruct      # une fois (≈ 4,7 Go)
ollama serve                         # http://localhost:11434/v1
docker compose up -d --build         # l'API joint Ollama via host.docker.internal
docker compose exec api python -m scripts.chat_demo --url http://localhost:8000 --scenario orientation --memoire
```

| Méthode | Route | Rôle |
|---|---|---|
| POST | `/sessions` | (SA-25) ouvre une session visiteur et renvoie `session_token`, à envoyer dans `X-Session-Token` |
| POST | `/chat/messages` | en-tête `X-Session-Token`, corps `{"content": "..."}` : réponse du LLM, langue détectée, mémoire |
| GET | `/chat/messages` | historique de la conversation |
| GET | `/chat/memoire` | profil mémorisé (niveau, section, moyenne, intérêts, préférences, contraintes, projet, formations évoquées) |

À chaque message (SA-36 / SA-37) :

1. détection de la langue : français, tunisien en graphie arabe, Arabizi, mélange (`app/llm/language.py`) ;
2. mise à jour de la **mémoire longue** du candidat (`conversations.memory`, migration 0003) ;
3. prompt = règles (pas d'invention, répondre dans la langue du candidat) + **catalogue publié lu en base**
   (frais, conditions, débouchés, passerelles, sources) + mémoire + **fenêtre des derniers messages** ;
4. appel au LLM. S'il est indisponible : `503 service_unavailable` et rien n'est enregistré ;
5. enregistrement du message, de la réponse (avec leur langue) et de la mémoire.

Les routes `/chat` réutilisent la session visiteur SA-25 (`GuestSession` : 401 si absente, fermée ou expirée ;
chaque message prolonge la session). Le RAG (autre epic) remplacera le contexte catalogue (`app/services/chat_context.py`).

Variables : `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TIMEOUT_S`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`,
`LLM_MEMORY_MAX_MESSAGES`, `LLM_MEMORY_MAX_CHARS`, `LLM_MEMORY_EXTRACTION` (`regles` ou `llm`), `LLM_PROVIDER=fake`
(LLM factice, sans serveur). Requêtes d'exemple : [requests/chat.http](requests/chat.http).

Tests du dialogue (SA-38) : `tests/test_chat_api.py`, `tests/test_dialogue_multitours.py` (LLM factice) ;
avec un vrai LLM : `LLM_LIVE_TESTS=1 pytest -m llm_live -s`.

## 7. Structure

```text
backend/
├── app/
│   ├── llm/             client LLM OpenAI-compatible, détection de langue, prompts, mémoire (SA-30)
│   ├── core/            config, database (engines), security (bcrypt/JWT), errors, ai_sql (garde-fou SQL IA)
│   ├── models/          SQLAlchemy : catalog (SA-12), identity + applications (SA-13), documents (SA-14)
│   ├── schemas/         Pydantic v2 (pagination, sources, formations/tarifs/conditions)
│   ├── repositories/    requêtes SQL (programs, dossier_scope = périmètre des responsables)
│   ├── services/        règles métier (visibilité, RBAC par établissement, archivage, audit)
│   └── api/             deps (JWT/RBAC) + v1/endpoints (health, formations, chat)
├── alembic/versions/    0001 schéma + triggers, 0002 vues ai_views + privilèges, 0003 mémoire des conversations
├── evaluation/          SA-31 : questions, jeu dialecte/Arabizi, comparaison des LLM, notebook Colab
├── seeds/seed.py        données DEMO idempotentes
├── docker/              init Postgres (rôles, bases, pgvector) + entrypoint API
├── docs/                erd.md, data_dictionary.md, normalisation.md, security.md, backlog_suggestions.md
├── requests/            collection .http
├── scripts/             gen_docs, issue_token, print_ddl
├── tests/               pytest (migrations, seed, règles DB, ai_readonly, périmètre, API, plateforme)
├── docker-compose.yml, Dockerfile, .env.example, SEED_DATA_NOTES.md
```

## 8. Documentation

- [docs/erd.md](docs/erd.md) : diagrammes Mermaid (générés)
- [docs/data_dictionary.md](docs/data_dictionary.md) : dictionnaire de données (généré)
- [docs/normalisation.md](docs/normalisation.md) : normalisation et règles en base
- [docs/llm_selection.md](docs/llm_selection.md) : sélection du LLM (SA-31)
- [docs/security.md](docs/security.md) : rôles PostgreSQL, outil SQL de l'IA, données personnelles
- [SEED_DATA_NOTES.md](SEED_DATA_NOTES.md) : **données fictives à remplacer**
- [docs/backlog_suggestions.md](docs/backlog_suggestions.md) : idées hors sprint
