"""SA-37 — Mémoire conversationnelle : extraction du profil, fusion, prompt et fenêtre d'historique.
Tests unitaires, sans base ni LLM."""

import pytest

from app.llm.memory import (
    ConversationMemory,
    HistoryItem,
    build_history,
    extract_profile,
    profile_from_llm,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("aslema, 9rit bac maths w jebt 15 de moyenne",
         {"moyenne": "15", "section_bac": "mathématiques", "niveau": "bachelier"}),
        ("عسلامة، قريت باك رياضيات وجبت 14", {"moyenne": "14", "section_bac": "mathématiques", "niveau": "bachelier"}),
        ("Bonjour, ena 3andi bac info avec 13 de moyenne", {"moyenne": "13", "section_bac": "informatique"}),
        ("moyenti 11.5 fel bac maths", {"moyenne": "11.5", "section_bac": "mathématiques"}),
        ("ena fi terminale sciences exp w n7eb nwalli ingénieur",
         {"niveau": "terminale", "section_bac": "sciences expérimentales", "objectif": "ingénieur"}),
        ("kamalt L2 fi ecole o5ra", {"niveau": "licence 2e année (bac+2)"}),
        ("Je veux devenir data scientist, quel parcours ?", {"objectif": "data scientist"}),
    ],
)
def test_extract_scalars(message, expected):
    found = extract_profile(message)
    for key, value in expected.items():
        assert found.get(key) == value, (key, found)


@pytest.mark.parametrize(
    ("message", "key", "values"),
    [
        ("nheb barcha l'informatique w el robotique", "interets", ["informatique", "robotique"]),
        ("نحب الإنفورماتيك برشا والذكاء الاصطناعي", "interets", ["informatique", "intelligence artificielle"]),
        ("J'adore les maths et l'informatique", "interets", ["informatique", "mathématiques"]),
        ("mouch mitakked, nheb 7aja pratique akthar mel théorie", "preferences", ["formation pratique"]),
        ("ma3andich flous barcha, ena men sfax", "contraintes", ["budget limité", "ville : Sfax"]),
        ("نحب نقرا في صفاقس، الفلوس غالية", "contraintes", ["budget limité", "ville : Sfax"]),
        ("nhésite bin prepa w licence info", "formations_evoquees",
         ["Cycle préparatoire intégré", "Licence en Informatique"]),
    ],
)
def test_extract_lists(message, key, values):
    assert extract_profile(message).get(key) == values


def test_no_false_positive_on_plain_question():
    assert extract_profile("9adech flous el inscription ?") == {}
    assert "interets" not in extract_profile("chnowa el formations elli famma ?")
    assert extract_profile("") == {}


def test_impossible_average_is_ignored():
    assert "moyenne" not in extract_profile("moyenne 35 sur 20")


def test_profile_from_llm_maps_keys():
    found = profile_from_llm({"section_bac": "maths", "interets": "robotique", "formation": "prépa",
                              "lieu": "Sfax", "inconnu": "x", "moyenne": None})
    assert found == {"section_bac": "maths", "interets": ["robotique"], "formations_evoquees": ["prépa"],
                     "contraintes": ["ville : Sfax"]}
    assert profile_from_llm(None) == {}


def test_memory_accumulates_and_round_trips():
    mem = ConversationMemory()
    mem.observe_user_message("aslema, 9rit bac maths w jebt 15", "arabizi")
    mem.observe_user_message("nheb el robotique", "arabizi")
    mem.observe_user_message("finalement j'ai eu 15.5 de moyenne", "fr")
    assert mem.profile["moyenne"] == "15.5"           # la valeur la plus récente gagne
    assert mem.profile["section_bac"] == "mathématiques"
    assert mem.profile["interets"] == ["robotique"]
    assert mem.turns == 3 and mem.language == "fr"
    again = ConversationMemory.from_json(mem.to_json())
    assert again == mem


def test_questions_are_bounded():
    mem = ConversationMemory()
    for i in range(20):
        mem.observe_user_message(f"question {i} " + "x" * 300, "fr")
    assert len(mem.questions) == 8
    assert mem.questions[-1].startswith("question 19") and len(mem.questions[-1]) == 200


def test_to_prompt():
    mem = ConversationMemory()
    assert "premier échange" in mem.to_prompt()
    mem.observe_user_message("9rit bac maths w jebt 15", "arabizi")
    mem.observe_user_message("9adech el prepa ?", "arabizi")
    prompt = mem.to_prompt()
    assert "Section du bac : mathématiques" in prompt
    assert "Moyenne : 15" in prompt
    assert "Encore inconnu : Centres d'intérêt" in prompt
    assert "Questions déjà posées : 9rit bac maths w jebt 15" in prompt
    assert "9adech el prepa" not in prompt  # la question en cours n'est pas « déjà posée »


def test_from_json_tolerates_empty():
    assert ConversationMemory.from_json({}) == ConversationMemory()
    assert ConversationMemory.from_json(None) == ConversationMemory()


def _dialogue(n: int) -> list[HistoryItem]:
    items = []
    for i in range(n):
        items += [HistoryItem("user", f"q{i}"), HistoryItem("assistant", f"r{i}")]
    return items


def test_history_window_keeps_most_recent_in_order():
    window = build_history(_dialogue(10), max_messages=4, max_chars=10_000)
    assert [m.content for m in window] == ["q8", "r8", "q9", "r9"]
    assert [m.role for m in window] == ["user", "assistant", "user", "assistant"]


def test_history_window_respects_char_budget_and_starts_with_user():
    items = [HistoryItem("user", "a" * 50), HistoryItem("assistant", "b" * 50), HistoryItem("user", "c" * 50),
             HistoryItem("assistant", "d" * 50)]
    window = build_history(items, max_messages=10, max_chars=160)
    assert [m.content[0] for m in window] == ["c", "d"]   # "b" tiendrait, mais la fenêtre commence par le candidat
    assert build_history([], max_messages=5, max_chars=100) == []
    assert build_history([HistoryItem("system", "x")], max_messages=5, max_chars=100) == []
