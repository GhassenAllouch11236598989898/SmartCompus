# Sécurité des données — SmartCampus AI (SA-16)

## 1. Rôles PostgreSQL (moindre privilège)

| Rôle | Utilisé par | Droits |
|---|---|---|
| `postgres` (superuser) | initialisation du conteneur uniquement | création des rôles, des bases et de l'extension `vector` |
| `smartcampus_owner` | `alembic upgrade`, `python -m seeds.seed` | propriétaire des schémas `public` et `ai_views` (DDL). Pas superuser, pas CREATEROLE |
| `smartcampus_app` | API FastAPI (`DATABASE_URL`) | `SELECT, INSERT, UPDATE` sur les tables de `public`, `USAGE` sur les séquences. **Pas de DELETE, pas de DDL**. `statement_timeout = 15s` |
| `ai_readonly` | outil SQL de l'agent IA (`AI_READONLY_DATABASE_URL`) | `USAGE` sur `ai_views` + `SELECT` sur ses vues, **et rien d'autre** |

Les rôles sont créés par [`docker/postgres/init/01-roles-and-databases.sh`](../docker/postgres/init/01-roles-and-databases.sh), qui ne s'exécute que sur un volume vide. Les `GRANT` sur les tables et les vues sont faits par la migration Alembic `0002`. Ils se rejouent donc de façon identique sur toute base (dev, test, prod).

Durcissements communs : `REVOKE ALL ON DATABASE … FROM PUBLIC`, `REVOKE ALL ON SCHEMA public FROM PUBLIC`. Le schéma `public` appartient à `smartcampus_owner`.

## 2. Outil SQL de l'agent IA

Le LLM génère du SQL. Le backend le contrôle **avant** de l'exécuter ([`app/core/ai_sql.py`](../app/core/ai_sql.py)), avec 4 couches indépendantes :

1. **Validation** (`validate_ai_sql`) : une seule instruction commençant par `SELECT`/`WITH`, sans `;` interne ni commentaire (`--`, `/* */`). Elle refuse aussi les fonctions et objets dangereux : `pg_sleep`, `set_config`, `current_setting`, `pg_read_*`, `lo_*`, `dblink`, `pg_catalog`, `information_schema`, `public`, `COPY`, `INTO`…
2. **Encapsulation** : `SELECT * FROM (<requête>) AS ai_query LIMIT :n`. Le **LIMIT est imposé** (`AI_SQL_MAX_ROWS`, 100 par défaut) même si la requête en contient un plus grand. Toute instruction non-SELECT y devient une erreur de syntaxe.
3. **Transaction** : `SET TRANSACTION READ ONLY` + `SET LOCAL statement_timeout` (`AI_SQL_STATEMENT_TIMEOUT_MS`, 3 s par défaut).
4. **Rôle `ai_readonly`** (filet de sécurité si les couches 1 à 3 sont contournées) :
   - `default_transaction_read_only = on`, `statement_timeout = 3s`, `idle_in_transaction_session_timeout = 10s`, `search_path = ai_views`, `CONNECTION LIMIT 10`, `NOINHERIT` ;
   - **aucun droit sur `public`** : `users`, `consents`, `conversations`, `messages`, `audit_log`, etc. sont illisibles.

### Vues exposées (schéma `ai_views`)

| Vue | Contenu | Exclu volontairement |
|---|---|---|
| `v_formations_public` | formations **publiées** : établissement, type, durée, modalités, source + date | brouillons, formations archivées |
| `v_tuition_fees_public` | tarifs des formations publiées, avec source | — |
| `v_admission_conditions_public` | conditions d'admission, avec source | — |
| `v_prerequisites_public`, `v_career_outcomes_public`, `v_pathways_public` | prérequis, débouchés, passerelles | — |
| `v_candidate_dossier_summary` | dossier : statut, campagne, formations visées, score QCM, prochain RDV, dernière décision, `ai_summary` | nom, email, téléphone, mot de passe, consentements, jetons de session, contenu des conversations |

> ⚠️ `v_candidate_dossier_summary` expose `candidate_id`. **L'outil de l'agent (epic agents) doit toujours filtrer par le `candidate_id` de l'utilisateur authentifié** (paramètre lié, jamais injecté par le LLM). Une protection RLS en base est proposée dans le backlog.

Les vues appartiennent à `smartcampus_owner` (`security_invoker = false`) : `ai_readonly` lit la vue sans aucun droit sur les tables sous-jacentes.

## 3. Données personnelles et secrets

- **Minimisation** : année de naissance seule, pas d'adresse, téléphone facultatif. Les pièces d'équivalence sont stockées hors base (métadonnées + SHA-256 seulement).
- **Mots de passe** : bcrypt (coût 12). CHECK en base qui refuse toute valeur qui n'est pas un hash.
- **Jetons de session anonymes** : seul le SHA-256 est stocké (`session_token_hash`).
- **Consentement** : `consents` horodaté (`granted_at`, `revoked_at`, `policy_version`).
- **Aucun secret loggé** : le middleware de log n'écrit que méthode, chemin, statut et durée. Pas d'en-têtes `Authorization`, pas de corps de requête. `audit_log.details` ne contient jamais de mot de passe ni de jeton.
- **Pas de suppression physique** : trigger `prevent_delete` + absence du privilège DELETE (voir [normalisation.md](normalisation.md)).

## 4. API

- JWT HS256 (`JWT_SECRET_KEY` ≥ 32 caractères, obligatoire via `.env`). L'émission des jetons appartient à l'epic Auth. En dev : `python -m scripts.issue_token <email>`.
- RBAC sur les routes d'écriture du catalogue :
  - `admin` : tous les établissements ;
  - `responsable_iit` / `responsable_isb` : **uniquement** les formations de leur établissement (ancien et nouvel établissement vérifiés lors d'un PUT/PATCH) ;
  - les autres rôles reçoivent 403.
- CORS limité aux origines `CORS_ORIGINS` (frontend Next.js).
