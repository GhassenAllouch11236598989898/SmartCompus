# Suggestions hors sprint SA-10 (non implémentées)

| # | Suggestion | Pourquoi |
|---|---|---|
| 1 | **Row-Level Security** sur les vues candidat (`v_candidate_dossier_summary`) avec `SET app.current_candidate_id` | Aujourd'hui le filtre par candidat repose sur l'outil de l'agent. La RLS le garantirait en base. |
| 2 | Extension `unaccent` + configuration FTS `french_unaccent` | La recherche « ingenieur » ne trouve pas encore « ingénieur ». |
| 3 | Tables `qcm_templates` et `email_templates` (gérées par l'admin) | Le cahier des charges mentionne des modèles QCM et e-mails. Pour l'instant on ne stocke qu'un `template_code`. |
| 4 | Référentiel fermé des intérêts et matières (table d'association) | À faire si le métier fige une liste (voir normalisation.md). |
| 5 | Anonymisation d'un candidat (droit à l'effacement, loi organique 2004-63) au lieu d'une suppression | Compatible avec la règle « aucune suppression physique ». |
| 6 | Partitionnement / rétention de `audit_log` et `messages` | Volumétrie à long terme. |
| 7 | Cache HTTP (ETag / `Cache-Control`) sur le catalogue public | Les données changent rarement et sont lues souvent (chatbot). |
| 8 | Contrôle de cohérence : formation d'une préinscription ∈ établissement de la campagne du dossier (trigger) | Aujourd'hui seule la couche applicative le garantit (epic préinscriptions). |
| 9 | Valider la dimension des embeddings (1024) avec l'équipe RAG | Changer la dimension impose une migration et une ré-indexation. |
| 10 | Endpoints CRUD pour prérequis, conditions, tarifs et débouchés | SA-20/21 n'expose que la lecture de ces sous-ressources. Ces données se modifient aujourd'hui via seed ou SQL. |
| 11 | Pagination par curseur sur `/formations` | Utile seulement si le catalogue devient volumineux. |
