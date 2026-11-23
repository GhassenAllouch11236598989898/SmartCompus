# SEED_DATA_NOTES — données de démonstration à remplacer

> ⚠️ **Toutes les données insérées par `python -m seeds.seed` sont FICTIVES.**
> Elles ont `is_demo = true` et tous les documents sources ont `version = 'DEMO'`.
> Aucune n'est une information officielle de l'IIT ou de l'ISB. Le groupe doit les remplacer
> par les informations validées (brochures, règlements, grilles tarifaires officielles) avant toute démonstration publique.

Requête pour lister tout ce qui reste à remplacer :

```sql
SELECT 'programs' AS t, code AS ref FROM programs WHERE is_demo
UNION ALL SELECT 'tuition_fees', program_id || ' ' || academic_year || ' ' || fee_type FROM tuition_fees WHERE is_demo
UNION ALL SELECT 'source_documents', title FROM source_documents WHERE version = 'DEMO';
```

## 1. Catalogue (à remplacer en priorité)

| Donnée | Valeur DEMO | Ce qu'il faut fournir |
|---|---|---|
| Nom officiel des établissements | `IIT — nom officiel à confirmer (DEMO)`, `ISB — nom officiel à confirmer (DEMO)` | Raison sociale, description, site web |
| Types de parcours | LICENCE, PREPA, INGENIERIE, MASTER | Liste exacte des parcours de l'ISB (MASTER est une **hypothèse**) |
| Formations IIT | `IIT-LIC-INFO` (6 sem.), `IIT-PREPA-MP` (4 sem.), `IIT-ING-GI` (6 sem.) | Intitulés, codes, durées, contenu, diplôme délivré, modalités |
| Formation brouillon | `IIT-ING-GC` (draft), pour tester la visibilité | Supprimable (passer en archived) |
| Formations ISB | `ISB-LIC-GEST` (6 sem.), `ISB-MAS-MKT` (4 sem., hybride), `ISB-LIC-ARCH` (archivée) | Formations réelles de l'ISB |
| Prérequis | ex. « Bac Maths ou Sciences exp. », « moyenne en maths ≥ 12 » | Prérequis officiels |
| Conditions d'admission 2026-2027 | moyennes minimales 10 / 11 / 12, QCM, entretien, équivalence | Règlement d'admission officiel |
| Débouchés | ex. « Ingénieur logiciel », « Assistant comptable » | Débouchés officiels |
| Passerelles | PREPA → ING, LIC → ING, ISB-LIC → ISB-MAS | Passerelles réglementaires et leurs conditions |
| **Tarifs 2026-2027** (TND) | inscription 300 (IIT) / 250 (ISB). Scolarité : LIC 5 900, PREPA 6 200, ING 7 500, ISB-LIC 5 200, ISB-MAS 6 800 | **Grille tarifaire officielle** |
| Tarifs 2025-2026 | scolarité = 95 % de 2026-2027 | Grille de l'année précédente (ou à retirer) |
| Modalités de paiement | « 1 ou 3 tranches » | Modalités officielles |
| Campagnes | « Admissions IIT/ISB 2026-2027 (DEMO) », 01/06 → 31/12/2026, statut open | Calendrier officiel |
| Documents sources | 5 documents `version = DEMO`, `uri = demo://…`, hash = SHA-256 d'une clé DEMO | Vrais fichiers, avec version, date d'édition et hash calculé sur le fichier |

## 2. Utilisateurs (mot de passe commun **`Demo2026!`**, comptes de démo uniquement)

Domaine e-mail `@demo.smartcampus.invalid` (TLD `.invalid` réservé : aucun e-mail réel ne peut partir).

| Email | Rôle |
|---|---|
| admin@… | admin |
| direction@… | direction |
| responsable.iit@… | responsable_iit (périmètre IIT) |
| responsable.isb@… | responsable_isb (périmètre ISB) |
| responsable.entretien@… | responsable_entretien |
| amine.candidat@…, yasmine.candidat@…, karim.candidat@…, salma.candidat@…, oussama.candidat@… | candidate |

## 3. Candidatures (scénarios fictifs)

| Candidat | Profil | Scénario |
|---|---|---|
| Amine (c1) | Bac maths 15,2, intérêt IA | **Dossier complet** : préinscription PREPA validée, recommandation confirmée, QCM 4/5 (5 questions), RDV terminé, entretien favorable, **décision « admitted »** par le responsable IIT, notification envoyée |
| Yasmine (c2) | Bac info 13,4 | Préinscription LIC soumise, **recommandation en attente de validation** (`pending`), RDV en ligne programmé le 15/01/2027 |
| Karim (c3) | L2 info (réorientation) | **Demande d'équivalence** `under_review` vers ING-GI, 2 pièces (métadonnées seulement), recommandation `adjusted` |
| Salma (c4) | Lycéenne | Dossier ouvert, préinscription brouillon, relance e-mail `pending` |
| Oussama (c5) | Bac éco-gestion | Préinscription ISB-LIC soumise (périmètre ISB) |

Conversations : c1 en **français**, c2 en **dialecte tunisien** (graphie arabe), c3 en **Arabizi**, plus **1 conversation anonyme** (`candidate_id = NULL`, premier message audio + consentement d'enregistrement). Les jetons de session sont des chaînes `demo-…`, et seul leur SHA-256 est stocké.

## 4. Documents / RAG

- 10 `document_chunks` liés aux formations concernées.
- **Embeddings FICTIFS** : vecteurs pseudo-aléatoires déterministes (`embedding_model = 'DEMO-fake-embedding'`). Ils n'ont **aucun sens sémantique** et doivent être recalculés par le pipeline RAG.
- 1 `sync_job` `full_sync` réussi + 2 `sync_logs`.
