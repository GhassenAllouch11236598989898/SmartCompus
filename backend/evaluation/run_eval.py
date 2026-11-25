"""SA-33 / SA-34 — Lance l'évaluation des LLM candidats et produit le rapport de comparaison.

Exemples (depuis backend/) :

    # 1. Vérifier la chaîne sans aucun modèle (LLM factice) :
    python -m evaluation.run_eval --dry-run

    # 2. Mesurer le détecteur de langue du backend (aucun LLM) :
    python -m evaluation.run_eval --suite detecteur

    # 3. Comparer les modèles servis par Ollama (ollama pull qwen2.5:7b-instruct ...) :
    python -m evaluation.run_eval --suite all --only qwen2.5-7b,llama3.1-8b --judge qwen2.5-7b

Suites :
- questions  (SA-32/33) : réponse ancrée dans le contexte catalogue + classification d'intention et de langue ;
- dialecte   (SA-34)    : traduction tunisien/Arabizi -> français (chrF), intention, langue, extraction du profil ;
- detecteur  (SA-34)    : précision de app.llm.language.detect_language sur les deux jeux de données.

Sorties : evaluation/results/<horodatage>/ (réponses brutes JSONL par modèle, summary.json, rapport.md).
"""

import argparse
import json
import logging
import os
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.llm.client import ChatMessage, FakeLLMClient, LLMClient, LLMError, OpenAICompatibleClient
from app.llm.language import detect_language
from evaluation import metrics as m
from evaluation import prompts as p
from evaluation.report import selection_scores, write_report

ROOT = Path(__file__).parent
logger = logging.getLogger("smartcampus.eval")


# ------------------------------------------------------------------ données
def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_questions() -> list[dict[str, Any]]:
    return load_jsonl(p.DATA_DIR / "questions_evaluation.jsonl")


def load_dialect() -> list[dict[str, Any]]:
    return load_jsonl(p.DATA_DIR / "dialecte_arabizi.jsonl")


def load_models(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ appels
def _call(client: LLMClient, system: str, user: str, *, json_mode: bool = False, max_tokens: int = 400) -> dict:
    try:
        r = client.chat([ChatMessage("system", system), ChatMessage("user", user)],
                        temperature=0.0, max_tokens=max_tokens, json_mode=json_mode)
        return {"texte": r.content, "latence_ms": r.latency_ms, "tokens_sortie": r.completion_tokens, "erreur": None}
    except LLMError as exc:
        return {"texte": "", "latence_ms": None, "tokens_sortie": None, "erreur": str(exc)}


def _classify(client: LLMClient, text: str) -> tuple[dict | None, dict]:
    call = _call(client, p.CLASSIFY_SYSTEM, text, json_mode=True, max_tokens=60)
    return m.parse_json_object(call["texte"]), call


def _judge(judge: LLMClient | None, context: str, question: str, answer: str) -> float | None:
    if judge is None or not answer:
        return None
    parsed = m.parse_json_object(_call(judge, p.JUDGE_SYSTEM, p.judge_user(context, question, answer),
                                       json_mode=True, max_tokens=60)["texte"])
    try:
        notes = [float(parsed[k]) for k in ("exactitude", "pertinence", "langue")]  # type: ignore[index]
    except (TypeError, KeyError, ValueError):
        return None
    return (sum(notes) / 3 - 1) / 4  # 1..5 -> 0..1


# ------------------------------------------------------------------ suites
def run_questions(client: LLMClient, items: list[dict], judge: LLMClient | None) -> list[dict]:
    context = p.catalogue_context()
    system = p.ASSISTANT_SYSTEM.format(context=context)
    rows = []
    for it in items:
        ans = _call(client, system, it["question"])
        detected = detect_language(ans["texte"]).language.value if ans["texte"] else "unknown"
        cls, cls_call = _classify(client, it["question"])
        rows.append({
            "id": it["id"], "suite": "questions", "langue": it["langue"], "categorie": it["categorie"],
            "question": it["question"], "reponse": ans["texte"], "erreur": ans["erreur"] or cls_call["erreur"],
            "latence_ms": ans["latence_ms"], "tokens_sortie": ans["tokens_sortie"],
            "rappel_mots_cles": m.keyword_recall(ans["texte"], it["mots_cles"]),
            "comportement_ok": m.behaviour_ok(it["comportement"], ans["texte"]) if ans["texte"] else False,
            "comportement_attendu": it["comportement"],
            "langue_reponse": detected, "score_langue": m.language_score(it["langue"], detected),
            "json_valide": cls is not None,
            "intention_ok": bool(cls) and cls.get("intention") == it["intention"],
            "langue_detectee_llm": (cls or {}).get("langue"),
            "langue_llm_ok": bool(cls) and cls.get("langue") == it["langue"],
            "juge": _judge(judge, context, it["question"], ans["texte"]),
        })
        logger.info("%s %s ok", it["id"], it["langue"])
    return rows


def run_dialect(client: LLMClient, items: list[dict]) -> list[dict]:
    rows = []
    for it in items:
        tr = _call(client, p.TRANSLATE_SYSTEM, it["texte"], max_tokens=150)
        cls, cls_call = _classify(client, it["texte"])
        ext_call = _call(client, p.EXTRACT_SYSTEM, it["texte"], json_mode=True, max_tokens=200)
        extracted = m.parse_json_object(ext_call["texte"])
        prec, rec, f1 = m.slot_scores(extracted, it["entites"])
        rows.append({
            "id": it["id"], "suite": "dialecte", "langue": it["langue"], "texte": it["texte"],
            "traduction": tr["texte"], "reference_fr": it["reference_fr"],
            "erreur": tr["erreur"] or cls_call["erreur"] or ext_call["erreur"],
            "latence_ms": tr["latence_ms"], "tokens_sortie": tr["tokens_sortie"],
            "chrf": round(m.chrf(tr["texte"], it["reference_fr"]), 2),
            "json_valide": cls is not None and extracted is not None,
            "intention_ok": bool(cls) and cls.get("intention") == it["intention"],
            "langue_detectee_llm": (cls or {}).get("langue"),
            "langue_llm_ok": bool(cls) and cls.get("langue") == it["langue"],
            "profil_extrait": extracted, "profil_precision": prec, "profil_rappel": rec, "profil_f1": f1,
        })
        logger.info("%s %s ok", it["id"], it["langue"])
    return rows


def run_detector(questions: list[dict], dialect: list[dict]) -> dict[str, Any]:
    """Précision du détecteur heuristique du backend (sert à messages.detected_language)."""
    family = {"tn_darija", "arabizi", "mixed"}
    pairs = [(q["langue"], q["question"]) for q in questions] + [(d["langue"], d["texte"]) for d in dialect]
    confusion: dict[str, Counter] = defaultdict(Counter)
    exact = fam = 0
    for gold, text in pairs:
        got = detect_language(text).language.value
        confusion[gold][got] += 1
        exact += got == gold
        fam += got == gold or (gold in family and got in family)
    return {"n": len(pairs), "precision": exact / len(pairs), "precision_famille": fam / len(pairs),
            "confusion": {k: dict(v) for k, v in confusion.items()}}


# ------------------------------------------------------------------ agrégation
def _rate(rows: list[dict], key: str) -> float | None:
    vals = [1.0 if r[key] else 0.0 for r in rows if r.get(key) is not None]
    return m.mean(vals)


def summarize(rows: list[dict]) -> dict[str, Any]:
    q = [r for r in rows if r["suite"] == "questions"]
    d = [r for r in rows if r["suite"] == "dialecte"]
    d_dialect = [r for r in d if r["langue"] in ("tn_darija", "arabizi", "mixed")]
    latencies = [r["latence_ms"] for r in rows if r.get("latence_ms") is not None]
    toks = [(r["tokens_sortie"], r["latence_ms"]) for r in rows if r.get("tokens_sortie") and r.get("latence_ms")]
    s: dict[str, Any] = {
        "n_appels_en_erreur": sum(1 for r in rows if r.get("erreur")),
        "latence_p50_ms": m.percentile(latencies, 0.5),
        "latence_p95_ms": m.percentile(latencies, 0.95),
        "tokens_par_s": (sum(t for t, _ in toks) / (sum(ms for _, ms in toks) / 1000)) if toks else None,
    }
    if q:
        answerable = [r for r in q if r["comportement_attendu"] == "repondre"]
        traps = [r for r in q if r["comportement_attendu"] != "repondre"]
        s["questions"] = {
            "n": len(q),
            "rappel_mots_cles": m.mean(r["rappel_mots_cles"] for r in answerable),
            "honnetete": _rate(traps, "comportement_ok"),
            "score_langue": m.mean(r["score_langue"] for r in q),
            "intention": _rate(q, "intention_ok"),
            "langue_llm": _rate(q, "langue_llm_ok"),
            "json_valide": _rate(q, "json_valide"),
            "juge": m.mean(r["juge"] for r in q),
            "par_langue": {
                lang: {
                    "n": len(sub),
                    "rappel_mots_cles": m.mean(r["rappel_mots_cles"] for r in sub
                                               if r["comportement_attendu"] == "repondre"),
                    "score_langue": m.mean(r["score_langue"] for r in sub),
                    "intention": _rate(sub, "intention_ok"),
                }
                for lang in ("fr", "tn_darija", "arabizi", "mixed")
                if (sub := [r for r in q if r["langue"] == lang])
            },
        }
    if d:
        s["dialecte"] = {
            "n": len(d_dialect),
            "chrf": m.mean(r["chrf"] for r in d_dialect),
            "intention": _rate(d_dialect, "intention_ok"),
            "langue_llm": _rate(d_dialect, "langue_llm_ok"),
            "profil_f1": m.mean(r["profil_f1"] for r in d_dialect),
            "json_valide": _rate(d, "json_valide"),
            "par_langue": {
                lang: {"n": len(sub), "chrf": m.mean(r["chrf"] for r in sub),
                       "intention": _rate(sub, "intention_ok"), "profil_f1": m.mean(r["profil_f1"] for r in sub)}
                for lang in ("tn_darija", "arabizi", "mixed")
                if (sub := [r for r in d if r["langue"] == lang])
            },
        }
    return s


# ------------------------------------------------------------------ CLI
def _fake_responder(messages):  # réponses plausibles pour --dry-run
    system, user = messages[0].content, messages[-1].content
    guess = detect_language(user).language.value
    if system.startswith("Tu analyses"):
        return json.dumps({"intention": "info_formation", "langue": guess})
    if system.startswith("Traduis"):
        return "Bonjour, je voudrais des informations sur la licence."
    if system.startswith("Extrais"):
        return '{"formation": "licence"}'
    if system.startswith("Tu es un évaluateur"):
        return '{"exactitude": 4, "pertinence": 4, "langue": 3}'
    return "La Licence en Informatique dure 3 ans. Frais : inscription 300 TND, scolarité 5 900 TND."


def build_client(cfg: dict[str, Any], dry_run: bool) -> LLMClient:
    if dry_run:
        return FakeLLMClient(responder=_fake_responder, model=f"fake:{cfg['nom']}")
    api_key = os.environ.get(cfg["api_key_env"]) if cfg.get("api_key_env") else None
    return OpenAICompatibleClient(cfg["base_url"], cfg["modele"], api_key=api_key,
                                  timeout_s=float(cfg.get("timeout_s", 180)), max_retries=1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", type=Path, default=ROOT / "models.json")
    ap.add_argument("--only", help="noms de modèles séparés par des virgules (défaut : modèles actifs)")
    ap.add_argument("--suite", choices=["questions", "dialecte", "detecteur", "all"], default="all")
    ap.add_argument("--judge", help="nom du modèle (models.json) utilisé comme juge LLM, optionnel")
    ap.add_argument("--limit", type=int, help="nombre max. d'items par suite (essai rapide)")
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--dry-run", action="store_true", help="LLM factice, aucun appel réseau")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    questions, dialect = load_questions(), load_dialect()
    if args.limit:
        questions, dialect = questions[: args.limit], dialect[: args.limit]

    run_dir = args.out / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {"date": datetime.now(UTC).isoformat(timespec="seconds"), "dry_run": args.dry_run,
                               "suite": args.suite, "modeles": {}}
    summary["detecteur"] = run_detector(questions, dialect)
    if args.suite == "detecteur":
        write_report(run_dir, summary, {})
        print(f"Détecteur de langue : {summary['detecteur']['precision']:.1%} -> {run_dir / 'rapport.md'}")
        return 0

    config = load_models(args.models)
    wanted = set(args.only.split(",")) if args.only else None
    models = [c for c in config["modeles"] if (c["nom"] in wanted if wanted else c.get("actif", True))]
    if not models:
        print("Aucun modèle sélectionné (voir --only et models.json).", file=sys.stderr)
        return 2
    judge_cfg = next((c for c in config["modeles"] if c["nom"] == args.judge), None) if args.judge else None
    judge = build_client(judge_cfg, args.dry_run) if judge_cfg else None
    summary["juge"] = args.judge

    for cfg in models:
        logger.info("=== %s (%s)", cfg["nom"], cfg["modele"])
        client = build_client(cfg, args.dry_run)
        rows: list[dict] = []
        if args.suite in ("questions", "all"):
            rows += run_questions(client, questions, judge)
        if args.suite in ("dialecte", "all"):
            rows += run_dialect(client, dialect)
        with (run_dir / f"brut_{cfg['nom']}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        summary["modeles"][cfg["nom"]] = {"meta": {k: cfg.get(k) for k in
                                                   ("modele", "hf_id", "params_b", "licence", "vram_q4_go",
                                                    "adaptabilite")},
                                          "resultats": summarize(rows)}

    summary["classement"] = selection_scores(summary["modeles"], config["criteres"])
    write_report(run_dir, summary, config["criteres"])
    print(f"Rapport : {run_dir / 'rapport.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
