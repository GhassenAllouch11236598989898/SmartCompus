"""SA-31 — Jeux d'évaluation (SA-32), métriques et chaîne de comparaison (SA-33/34). Sans base ni réseau."""

import json

import pytest

from evaluation import metrics as m
from evaluation import prompts as p
from evaluation import run_eval
from evaluation.report import selection_scores

LANGS = {"fr", "ar", "tn_darija", "arabizi", "en", "mixed"}


def test_questions_dataset_is_valid():
    items = run_eval.load_questions()
    assert len(items) >= 50
    assert len({i["id"] for i in items}) == len(items)
    for it in items:
        assert it["langue"] in LANGS
        assert it["intention"] in p.INTENTIONS
        assert it["comportement"] in {"repondre", "dire_inconnu", "recentrer"}
        assert it["question"].strip()
        assert it["comportement"] != "repondre" or it["mots_cles"]
    by_lang = {lang: sum(1 for i in items if i["langue"] == lang) for lang in ("fr", "tn_darija", "arabizi", "mixed")}
    assert by_lang["arabizi"] >= 15 and by_lang["tn_darija"] >= 10 and by_lang["mixed"] >= 3
    # Questions pièges : formation absente du catalogue et hors sujet, dans chaque langue principale.
    for lang in ("fr", "tn_darija", "arabizi"):
        kinds = {i["comportement"] for i in items if i["langue"] == lang}
        assert {"dire_inconnu", "recentrer"} <= kinds


def test_dialect_dataset_is_valid():
    items = run_eval.load_dialect()
    assert len(items) >= 40
    for it in items:
        assert it["langue"] in LANGS
        assert it["intention"] in p.INTENTIONS
        assert it["reference_fr"].strip()
        assert set(it["entites"]) <= set(p.SLOTS)


def test_normalize():
    assert m.normalize("Ingénieur  À 5 200 TND") == "ingenieur a 5200 tnd"
    assert m.normalize("أهلاً") == "اهلا"


def test_keyword_recall_with_alternatives():
    assert m.keyword_recall("La prépa dure 2 ans, puis le cycle ingénieur.", ["prépa|prepa", "ingénieur", "licence"]) == pytest.approx(2 / 3)
    assert m.keyword_recall("scolarité 5.200 DT", ["5200"]) == 1.0
    assert m.keyword_recall("x", []) is None


def test_language_score():
    assert m.language_score("arabizi", "arabizi") == 1.0
    assert m.language_score("arabizi", "tn_darija") == 0.5
    assert m.language_score("mixed", "arabizi") == 1.0
    assert m.language_score("mixed", "fr") == 0.5
    assert m.language_score("arabizi", "fr") == 0.0


def test_behaviour():
    assert m.behaviour_ok("dire_inconnu", "Malheureusement, nous n'avons pas de formation en médecine.")
    assert m.behaviour_ok("dire_inconnu", "sorry, ma3andnach architecture fel IIT")
    assert m.behaviour_ok("dire_inconnu", "ماعندناش طب، اتصل بالإدارة")
    assert not m.behaviour_ok("dire_inconnu", "La bourse d'excellence est de 2000 TND.")
    assert not m.behaviour_ok("dire_inconnu", "Malheureusement la bourse est de 2000 TND.")  # montant inventé
    assert m.behaviour_ok("recentrer", "Je suis là pour l'orientation : quelle formation vous intéresse ?")
    assert not m.behaviour_ok("recentrer", "Voici un poème sur la mer...")
    assert m.behaviour_ok("repondre", "La licence dure 3 ans.")


def test_chrf():
    assert m.chrf("Combien coûte la licence ?", "Combien coûte la licence ?") == pytest.approx(100.0)
    assert m.chrf("", "abc") == 0.0
    good = m.chrf("Combien coûte la licence par an ?", "Combien coûte la licence par an ?")
    close = m.chrf("Quel est le prix de la licence ?", "Combien coûte la licence par an ?")
    bad = m.chrf("Il fait beau.", "Combien coûte la licence par an ?")
    assert good > close > bad


def test_parse_json_object():
    assert m.parse_json_object('```json\n{"intention": "tarifs"}\n```') == {"intention": "tarifs"}
    assert m.parse_json_object('Voici : {"a": {"b": 1}} fin') == {"a": {"b": 1}}
    assert m.parse_json_object("pas de json") is None
    assert m.parse_json_object("{cassé} puis {\"ok\": true}") == {"ok": True}


def test_slot_scores():
    gold = {"section_bac": "math", "moyenne": "15", "interets": ["informatique", "robotique"]}
    assert m.slot_scores({"section_bac": "Mathématiques", "moyenne": 15, "interets": ["Informatique", "Robotique"]}, gold)[2] == 1.0
    p_, r_, f1 = m.slot_scores({"section_bac": "maths", "lieu": "Sfax"}, gold)
    assert (p_, r_) == (0.5, pytest.approx(1 / 3)) and 0 < f1 < 1
    assert m.slot_scores({}, {}) == (1.0, 1.0, 1.0)
    assert m.slot_scores(None, gold)[2] == 0.0


def test_percentile():
    assert m.percentile([1, 2, 3, 4], 0.5) == 2.5
    assert m.percentile([], 0.5) is None


def test_selection_scores_ranks_and_ignores_missing():
    weights = {"qualite_reponses": 0.5, "latence": 0.5}
    models = {
        "a": {"meta": {}, "resultats": {"questions": {"rappel_mots_cles": 0.9}, "latence_p50_ms": 1000}},
        "b": {"meta": {}, "resultats": {"questions": {"rappel_mots_cles": 0.5}, "latence_p50_ms": 10000}},
    }
    ranking = selection_scores(models, weights)
    assert [r["modele"] for r in ranking] == ["a", "b"]
    assert ranking[0]["score"] == pytest.approx(0.95)
    assert ranking[1]["score"] == pytest.approx(0.25)


def test_dry_run_end_to_end(tmp_path):
    code = run_eval.main(["--dry-run", "--only", "qwen2.5-7b,mistral-7b", "--judge", "qwen2.5-7b",
                          "--limit", "6", "--out", str(tmp_path)])
    assert code == 0
    run_dir = next(tmp_path.iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert set(summary["modeles"]) == {"qwen2.5-7b", "mistral-7b"}
    assert summary["classement"][0]["score"] > 0
    assert (run_dir / "brut_qwen2.5-7b.jsonl").exists()
    report = (run_dir / "rapport.md").read_text(encoding="utf-8")
    assert "Classement" in report and "Arabizi" in report


def test_detector_suite_only(tmp_path):
    assert run_eval.main(["--suite", "detecteur", "--out", str(tmp_path)]) == 0
    summary = json.loads((next(tmp_path.iterdir()) / "summary.json").read_text(encoding="utf-8"))
    assert summary["detecteur"]["precision"] >= 0.9


def test_unknown_model_selection_fails(tmp_path):
    assert run_eval.main(["--dry-run", "--only", "inexistant", "--out", str(tmp_path)]) == 2
