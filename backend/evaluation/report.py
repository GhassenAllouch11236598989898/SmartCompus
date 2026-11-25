"""SA-33 — Score de sélection pondéré et rapport Markdown de comparaison des modèles."""

import json
from pathlib import Path
from typing import Any


def _get(d: dict, *path: str) -> float | None:
    for k in path:
        if not isinstance(d, dict) or d.get(k) is None:
            return None
        d = d[k]
    return d  # type: ignore[return-value]


def _avg(*values: float | None) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def criteria_for(model: dict[str, Any]) -> dict[str, float | None]:
    """Ramène chaque critère de la grille entre 0 et 1."""
    r, meta = model["resultats"], model["meta"]
    juge = _get(r, "questions", "juge")
    kw = _get(r, "questions", "rappel_mots_cles")
    chrf = _get(r, "dialecte", "chrf")
    p50 = r.get("latence_p50_ms")
    return {
        # Le juge LLM, s'il est disponible, est combiné au rappel de mots-clés (plus robuste).
        "qualite_reponses": _avg(kw, juge),
        "comprehension_dialecte": _avg(None if chrf is None else chrf / 100,
                                       _get(r, "dialecte", "intention"), _get(r, "dialecte", "profil_f1"),
                                       _get(r, "questions", "par_langue", "arabizi", "rappel_mots_cles"),
                                       _get(r, "questions", "par_langue", "tn_darija", "rappel_mots_cles")),
        "intentions": _avg(_get(r, "questions", "intention"), _get(r, "dialecte", "intention")),
        "fidelite_langue": _get(r, "questions", "score_langue"),
        "honnetete": _get(r, "questions", "honnetete"),
        # 1 s ou moins -> 1 ; 10 s ou plus -> 0 (latence médiane par appel).
        "latence": None if p50 is None else max(0.0, min(1.0, 1 - (p50 / 1000 - 1) / 9)),
        "adaptabilite": meta.get("adaptabilite"),
    }


def selection_scores(models: dict[str, dict[str, Any]], weights: dict[str, float]) -> list[dict[str, Any]]:
    ranking = []
    for name, model in models.items():
        crit = criteria_for(model)
        used = {k: w for k, w in weights.items() if crit.get(k) is not None}
        total_w = sum(used.values())
        score = sum(crit[k] * w for k, w in used.items()) / total_w if total_w else 0.0  # type: ignore[operator]
        ranking.append({"modele": name, "score": round(score, 4), "criteres": crit})
    return sorted(ranking, key=lambda x: x["score"], reverse=True)


def _pct(v: float | None) -> str:
    return "–" if v is None else f"{100 * v:.0f} %"


def _num(v: float | None, fmt: str = "{:.0f}") -> str:
    return "–" if v is None else fmt.format(v)


def write_report(run_dir: Path, summary: dict[str, Any], weights: dict[str, float]) -> None:
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# Rapport d'évaluation LLM — {summary['date']}", ""]
    if summary.get("dry_run"):
        lines += ["> **Exécution à blanc (`--dry-run`)** : LLM factice. Les chiffres ne mesurent pas un vrai modèle.", ""]

    det = summary["detecteur"]
    lines += ["## Détecteur de langue du backend (SA-34)", "",
              f"{det['n']} messages : précision exacte **{_pct(det['precision'])}**, "
              f"précision par famille (tunisien/Arabizi/mixte confondus) **{_pct(det['precision_famille'])}**.", "",
              "| Attendu | Détecté |", "|---|---|"]
    lines += [f"| {gold} | {', '.join(f'{k}: {v}' for k, v in sorted(got.items()))} |"
              for gold, got in sorted(det["confusion"].items())]
    lines.append("")

    models = summary.get("modeles") or {}
    if not models:
        (run_dir / "rapport.md").write_text("\n".join(lines), encoding="utf-8")
        return

    lines += ["## Classement (grille de sélection SA-31)", "",
              "Poids : " + ", ".join(f"{k} {int(w * 100)} %" for k, w in weights.items()), "",
              "| Rang | Modèle | Score | " + " | ".join(weights) + " |",
              "|---|---|---|" + "---|" * len(weights)]
    for i, row in enumerate(summary.get("classement", []), 1):
        lines.append(f"| {i} | {row['modele']} | **{row['score']:.2f}** | "
                     + " | ".join(_num(row["criteres"].get(k), "{:.2f}") for k in weights) + " |")

    lines += ["", "## Questions d'évaluation (SA-32 / SA-33)", "",
              "| Modèle | Mots-clés | Honnêteté | Langue de réponse | Intention | Langue (LLM) | JSON valide | Juge | p50 (ms) | p95 (ms) | tokens/s | Erreurs |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, mdl in models.items():
        r, q = mdl["resultats"], mdl["resultats"].get("questions", {})
        lines.append(f"| {name} | {_pct(q.get('rappel_mots_cles'))} | {_pct(q.get('honnetete'))} | "
                     f"{_pct(q.get('score_langue'))} | {_pct(q.get('intention'))} | {_pct(q.get('langue_llm'))} | "
                     f"{_pct(q.get('json_valide'))} | {_pct(q.get('juge'))} | {_num(r.get('latence_p50_ms'))} | "
                     f"{_num(r.get('latence_p95_ms'))} | {_num(r.get('tokens_par_s'), '{:.1f}')} | "
                     f"{r.get('n_appels_en_erreur', 0)} |")

    lines += ["", "### Par langue de la question", "",
              "| Modèle | Langue | n | Mots-clés | Langue de réponse | Intention |", "|---|---|---|---|---|---|"]
    for name, mdl in models.items():
        for lang, v in (mdl["resultats"].get("questions", {}).get("par_langue") or {}).items():
            lines.append(f"| {name} | {lang} | {v['n']} | {_pct(v['rappel_mots_cles'])} | "
                         f"{_pct(v['score_langue'])} | {_pct(v['intention'])} |")

    lines += ["", "## Compréhension du dialecte tunisien et de l'Arabizi (SA-34)", "",
              "| Modèle | n | chrF traduction → FR | Intention | Langue (LLM) | Profil F1 | JSON valide |",
              "|---|---|---|---|---|---|---|"]
    for name, mdl in models.items():
        d = mdl["resultats"].get("dialecte", {})
        lines.append(f"| {name} | {d.get('n', 0)} | {_num(d.get('chrf'), '{:.1f}')} | {_pct(d.get('intention'))} | "
                     f"{_pct(d.get('langue_llm'))} | {_pct(d.get('profil_f1'))} | {_pct(d.get('json_valide'))} |")
    lines += ["", "| Modèle | Langue | n | chrF | Intention | Profil F1 |", "|---|---|---|---|---|---|"]
    for name, mdl in models.items():
        for lang, v in (mdl["resultats"].get("dialecte", {}).get("par_langue") or {}).items():
            lines.append(f"| {name} | {lang} | {v['n']} | {_num(v['chrf'], '{:.1f}')} | {_pct(v['intention'])} | "
                         f"{_pct(v['profil_f1'])} |")

    lines += ["", "## Modèles", "", "| Modèle | Identifiant | Paramètres (B) | Licence | VRAM Q4 (Go) |",
              "|---|---|---|---|---|"]
    for name, mdl in models.items():
        meta = mdl["meta"]
        lines.append(f"| {name} | `{meta.get('hf_id') or meta.get('modele')}` | {meta.get('params_b')} | "
                     f"{meta.get('licence')} | {meta.get('vram_q4_go')} |")
    lines += ["", "Réponses brutes : `brut_<modele>.jsonl` (à relire pour l'analyse qualitative)."]
    (run_dir / "rapport.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
