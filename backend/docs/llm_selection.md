# SA-31 — Sélection du modèle LLM (fiche de décision)

## Besoin (cahier des charges)

- Comprendre et générer du **français**, du **dialecte tunisien** (graphie arabe) et de l'**Arabizi**, avec code-switching.
- Répondre **uniquement à partir des sources officielles** IIT/ISB (RAG) et citer la source, sans halluciner.
- Produire du **JSON fiable** (intention, extraction du profil candidat) pour l'orchestration LangGraph.
- Modèle **open-source** adaptable par **LoRA/QLoRA** au contexte tunisien.
- Tourner sur le matériel du projet : un GPU grand public ou Colab T4 (16 Go), quantifié en 4 bits.

## Modèles candidats

| Modèle | Taille | Licence | VRAM Q4 | Atouts / limites a priori |
|---|---|---|---|---|
| Qwen2.5-7B-Instruct | 7,6 B | Apache-2.0 | ~5,5 Go | Très bon multilingue (arabe, français), JSON fiable, contexte 128k, écosystème QLoRA (Unsloth, PEFT) |
| Qwen3-8B | 8,2 B | Apache-2.0 | ~6 Go | Successeur de Qwen2.5, mode « raisonnement » à désactiver (latence) |
| Llama-3.1-8B-Instruct | 8 B | Llama 3.1 Community | ~5,5 Go | Référence très utilisée, arabe plus faible |
| Gemma-2-9B-it | 9,2 B | Gemma Terms | ~6,5 Go | Bon en génération, contexte 8k seulement |
| Aya-Expanse-8B | 8 B | CC-BY-NC-4.0 | ~5,5 Go | Conçu pour 23 langues dont l'arabe ; licence non commerciale |
| Mistral-7B-Instruct-v0.3 | 7,2 B | Apache-2.0 | ~4,5 Go | Rapide, bon français, arabe faible |
| Atlas-Chat-9B (optionnel) | 9,2 B | Gemma Terms | ~6,5 Go | Spécialisé darija marocaine (proche du tunisien), servi par vLLM |

## Protocole

Voir [`evaluation/README.md`](../evaluation/README.md) : 59 questions (SA-32) en 4 registres de langue,
42 phrases dialecte / Arabizi (SA-34), métriques automatiques et score pondéré (SA-33).
Tous les modèles reçoivent les mêmes prompts, à température 0, avec le même contexte catalogue.

## Résultats

> À compléter avec le `rapport.md` du run final (`python -m evaluation.run_eval --suite all --judge qwen2.5-7b`,
> ou le notebook Colab). Copier ici le tableau « Classement » et 3 ou 4 exemples de réponses marquants
> (bonne réponse en Arabizi, hallucination évitée, erreur typique).

| Rang | Modèle | Score | Dialecte | Qualité | Honnêteté | Latence p50 |
|---|---|---|---|---|---|---|
| | | | | | | |

Détecteur de langue du backend (`app/llm/language.py`, aucune dépendance) : 101/101 messages des deux jeux de
données correctement classés. Ces jeux ont servi à le mettre au point : le chiffre est donc optimiste. Les tests
`tests/test_llm_language.py` ajoutent des phrases non vues.

## Décision

**Choix provisoire : Qwen2.5-7B-Instruct** (repli : Qwen3-8B), à confirmer par le run final :

- licence Apache-2.0, compatible avec un déploiement par l'IIT/ISB ;
- meilleur compromis connu en arabe + français parmi les modèles 7-8B, et sorties JSON fiables ;
- QLoRA 4 bits possible sur un seul T4 16 Go (Unsloth / PEFT), ce qui permet l'adaptation tunisien/Arabizi ;
- servi par Ollama ou vLLM derrière l'API OpenAI-compatible : le backend (SA-36) ne dépend pas du modèle,
  le changer ne demande qu'une variable d'environnement (`LLM_MODEL`).

Si le run final classe un autre modèle devant avec un écart de plus de 0,05 de score, retenir ce modèle et mettre
à jour `LLM_MODEL` dans `.env.example`.

## Suite

- Adapter le modèle retenu en **QLoRA** sur des dialogues tunisien / Arabizi, puis relancer la même évaluation
  pour mesurer le gain (même protocole, même jeu de test : ne pas entraîner sur ces questions).
- Enrichir les jeux de test avec de vrais messages de candidats (anonymisés).
