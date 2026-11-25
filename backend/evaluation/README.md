# SA-31 — Évaluation et sélection du LLM

Story **SA-31** de l'epic **SA-30 « Sélection et intégration du LLM »** :

| Tâche | Livrable |
|---|---|
| **SA-32** Préparer les questions pour évaluer les LLM | [`data/questions_evaluation.jsonl`](data/questions_evaluation.jsonl) (59 questions) et [`data/contexte_catalogue.md`](data/contexte_catalogue.md) |
| **SA-33** Comparer les performances des modèles LLM | [`run_eval.py`](run_eval.py), [`metrics.py`](metrics.py), [`report.py`](report.py), [`models.json`](models.json), notebook Colab [`notebooks/`](notebooks/SA33_comparaison_llm_colab.ipynb) |
| **SA-34** Évaluer la compréhension du dialecte tunisien et de l'Arabizi | [`data/dialecte_arabizi.jsonl`](data/dialecte_arabizi.jsonl) (42 phrases) + détecteur de langue du backend [`app/llm/language.py`](../app/llm/language.py) |

La décision et sa justification sont dans [`docs/llm_selection.md`](../docs/llm_selection.md).

## 1. Jeux de données

### Questions d'évaluation (SA-32)

Chaque ligne : `id`, `langue` (`fr`, `tn_darija`, `arabizi`, `mixed`), `categorie`, `intention`, `question`,
`mots_cles` (groupes de variantes `a|b` qui doivent apparaître dans une bonne réponse) et `comportement` attendu :

- `repondre` : la réponse est dans le contexte catalogue ;
- `dire_inconnu` : formation ou information **absente** (médecine, bourse...). Le modèle doit le dire **sans inventer de montant** (test d'hallucination) ;
- `recentrer` : demande hors sujet (poème, football, recette). Le modèle doit ramener la conversation vers l'orientation.

| Langue | Questions |
|---|---|
| Français | 20 |
| Dialecte tunisien (graphie arabe) | 14 |
| Arabizi | 20 |
| Mélange tunisien / français | 5 |

Les questions couvrent les 10 intentions du chatbot (formations, conditions d'admission, frais, orientation,
comparaison, débouchés, préinscription, calendrier, salutation, hors sujet). Le LLM reçoit le même
**contexte catalogue** (simulation d'un résultat RAG à partir des données DEMO du seed), afin de mesurer sa capacité
à répondre de façon ancrée, et non ses connaissances générales.

### Dialecte et Arabizi (SA-34)

42 phrases de candidats (20 Arabizi, 15 tunisien en graphie arabe, 3 mélanges, 4 phrases de contrôle FR/AR/EN),
chacune avec sa **traduction de référence en français**, son intention et les **informations de profil** attendues
(section du bac, moyenne, intérêts, contraintes, formation visée...).

## 2. Métriques

| Métrique | Calcul |
|---|---|
| Rappel de mots-clés | part des groupes de mots-clés retrouvés dans la réponse (normalisation : accents, lettres arabes, milliers « 5 200 » = « 5200 ») |
| Honnêteté | part des questions pièges bien gérées (`dire_inconnu` sans montant inventé, `recentrer`) |
| Fidélité de langue | langue de la réponse = langue de la question (1), même famille dialectale (0,5), sinon 0 |
| Intention / langue (LLM) | exactitude de la classification JSON du modèle |
| JSON valide | part des sorties JSON exploitables (nécessaire pour l'agent LangGraph) |
| chrF | similarité en n-grammes de caractères (0-100) entre la traduction du modèle et la référence française |
| Profil F1 | précision et rappel des informations de profil extraites |
| Juge LLM (option `--judge`) | note 1-5 exactitude / pertinence / langue, ramenée à 0-1 |
| Latence p50 / p95, tokens/s | mesurées par appel |

Le **score de sélection** est la moyenne pondérée de 7 critères (poids dans `models.json`) :
compréhension du dialecte 30 %, qualité des réponses 20 %, intentions 10 %, fidélité de langue 10 %,
honnêteté 10 %, latence 10 %, adaptabilité (licence + QLoRA sur un GPU 16 Go) 10 %.

## 3. Lancer l'évaluation

Prérequis : un serveur **OpenAI-compatible**. Le plus simple est [Ollama](https://ollama.com) :

```powershell
ollama pull qwen2.5:7b-instruct
ollama pull llama3.1:8b
# ... (voir models.json)
cd backend
.venv\Scripts\python.exe -m evaluation.run_eval --suite all --only qwen2.5-7b,llama3.1-8b --judge qwen2.5-7b
```

Sans GPU local : ouvrir [`notebooks/SA33_comparaison_llm_colab.ipynb`](notebooks/SA33_comparaison_llm_colab.ipynb)
dans Google Colab (GPU T4 gratuit), qui installe Ollama, télécharge les modèles et produit le rapport.

Autres commandes :

```powershell
python -m evaluation.run_eval --dry-run              # chaîne complète avec un LLM factice (aucun réseau)
python -m evaluation.run_eval --suite detecteur      # précision du détecteur de langue du backend
python -m evaluation.run_eval --limit 5 --only qwen2.5-7b   # essai rapide
```

Chaque exécution crée `evaluation/results/<horodatage>/` avec `rapport.md` (tableaux de comparaison),
`summary.json` et les réponses brutes `brut_<modele>.jsonl` pour l'analyse qualitative.
**Commiter le dossier du run final** : c'est la preuve de la sélection pour la présentation.

## 4. Tests

```powershell
python -m pytest tests/test_llm_language.py tests/test_llm_evaluation.py tests/test_llm_client.py
```

Ces tests n'utilisent ni la base ni le réseau.
