# Modèle relationnel — normalisation et règles transverses (SA-11)

Voir aussi : [erd.md](erd.md) (diagrammes) et [data_dictionary.md](data_dictionary.md) (colonnes et contraintes).

## 1. Niveau de normalisation visé : 3FN (et BCNF pour le catalogue)

| Forme normale | Comment elle est respectée |
|---|---|
| **1FN** | Valeurs atomiques. Les éléments répétés du catalogue ont leurs propres tables : prérequis, conditions, débouchés, passerelles, tarifs. Les pièces d'une équivalence sont dans `equivalence_documents`. Les questions et réponses QCM sont des lignes. |
| **2FN** | Les clés primaires sont des `id` techniques simples. Les clés naturelles composées (ex. `tuition_fees (program_id, academic_year, fee_type)`) sont des `UNIQUE`, et chaque attribut non clé dépend de la clé entière. |
| **3FN** | Pas de dépendance transitive. L'établissement d'un dossier **n'est pas stocké** : il se déduit de `dossiers.campaign_id → admission_campaigns.institution_id`. Le candidat d'une préinscription se déduit de `dossier_id`. Le libellé d'un type de parcours est dans `program_types`, pas dans `programs`. |
| **BCNF** | Dans le catalogue, chaque déterminant est une clé candidate (`institutions.code`, `program_types.code`, `programs.code`). |

### Dénormalisations assumées (justifiées)

| Choix | Justification |
|---|---|
| `candidate_profiles.interests`, `preferred_subjects` en `text[]` | Mots-clés libres, toujours lus en bloc par l'agent IA, jamais joints ni contraints. Une table d'association compliquerait le profil sans gain fonctionnel. Une table de référentiel est à prévoir si le métier fige une liste fermée (voir backlog). |
| `admission_conditions.eligible_bac_sections` en `text[]` | Même raisonnement : liste courte, toujours lue avec la condition. |
| `programs.search_vector` (colonne générée) | Redondance calculée et **maintenue par PostgreSQL** (`GENERATED ALWAYS … STORED`), donc sans risque d'incohérence. Elle sert à la recherche plein texte (index GIN). |
| `recommendations.cited_sources`, `qcm_questions.choices`, `audit_log.details` en JSONB | Données semi-structurées produites par l'IA ou le journal, lues en bloc. Les contraintes essentielles restent en CHECK (ex. `choices` est un tableau d'au moins 2 éléments). |
| `qcm.score` (agrégat de `qcm_answers.points_awarded`) | Il fige le score au moment de la clôture du QCM : c'est la valeur montrée au responsable d'entretien. CHECK `score <= max_score`. |

## 2. Règles transverses implémentées en base

| Règle (cahier des charges) | Mise en œuvre |
|---|---|
| Traçabilité de chaque info du catalogue | `source_document_id NOT NULL` + FK `RESTRICT` sur `programs`, `program_prerequisites`, `admission_conditions`, `career_outcomes`, `program_pathways`, `tuition_fees`, `admission_campaigns`. Le document porte type, version, date, hash SHA-256 et statut. |
| Données de démonstration identifiables | Colonne `is_demo` sur toutes les tables métier, plus des sources dont la version vaut `DEMO`. |
| Pas de suppression physique des candidatures | Trigger `prevent_delete()` (BEFORE DELETE ⇒ exception) sur les tables de candidature, d'identité et du catalogue. En plus, le rôle applicatif n'a **pas** le privilège DELETE. On archive via les statuts. |
| Horodatages | `created_at` / `updated_at` partout, avec le trigger `set_updated_at()`. |
| Historique | Trigger `log_status_change()` : chaque INSERT ou changement de `status` de dossiers, préinscriptions, équivalences, QCM, rendez-vous, recommandations (`review_status`) et formations est écrit dans `status_history`. `changed_by` vient de `SET LOCAL app.current_user_id`. `audit_log` est **append-only** (trigger `prevent_update_delete`). |
| Décision officielle = humain responsable | Trigger `assert_human_responsable()` sur `decisions.responsible_id`, `recommendations.reviewed_by` et `equivalence_requests.reviewed_by`. L'utilisateur doit être actif, **pas** un compte technique (`is_service_account = false`) et avoir un rôle `responsable_*`. |
| Un dossier actif par candidat et par campagne | Index unique partiel `uq_dossiers_active_candidate_campaign … WHERE status NOT IN ('enrolled','withdrawn','closed')`. |
| Visiteur anonyme | `conversations.candidate_id` est nullable. Le visiteur est identifié par `session_token_hash` (SHA-256, jamais le jeton brut). Le rattachement au compte se fait via `attached_at` (CHECK). |
| Mots de passe hachés | CHECK `password_hash ~ '^\$(2[aby]\|argon2id?)\$'` : un mot de passe en clair est refusé par la base. |
| Consentement horodaté | `consents.granted_at NOT NULL`, `policy_version`, `revoked_at >= granted_at`. |
| Périmètre des responsables | Le filtre applicatif `app/repositories/dossier_scope.py::scoped_dossiers(user)` repose sur `roles.institution_id` et sur les rendez-vous organisés (testé en SA-22). |

## 3. Conventions

- Tables et colonnes en anglais `snake_case`. Contraintes nommées de façon déterministe (`pk_`, `fk_`, `uq_`, `ck_`, `ix_`).
- Statuts en **ENUM PostgreSQL natifs** (valeurs en minuscules).
- Clés étrangères en `ON DELETE RESTRICT` : aucune cascade ne peut effacer un historique.
- Années académiques au format `AAAA-AAAA` (CHECK), montants en `NUMERIC(12,3)` + devise ISO 4217.
