"""SA-38 — Tests du dialogue multi-tours avec le LLM.

Scénarios rejoués de bout en bout via l'API (/chat), base PostgreSQL réelle, LLM factice « espion »
qui enregistre chaque prompt : on vérifie ce que le LLM reçoit à chaque tour (historique, mémoire,
consigne de langue) et ce qui est enregistré.

Le dernier test parle à un vrai LLM ; il ne tourne que si LLM_LIVE_TESTS=1 (serveur Ollama/vLLM lancé) :

    LLM_LIVE_TESTS=1 python -m pytest tests/test_dialogue_multitours.py -m llm_live -s
"""

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.llm.client import FakeLLMClient, get_llm_client
from app.llm.language import detect_language
from app.main import create_app

CHAT = "/api/v1/chat"


class SpyLLM(FakeLLMClient):
    """Répond « Réponse n » et garde chaque prompt reçu."""

    def __init__(self):
        super().__init__(responder=lambda msgs: f"Réponse {len(self.calls)}")


def _client(db: Session, llm) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm
    return TestClient(app)


@pytest.fixture
def spy() -> SpyLLM:
    return SpyLLM()


@pytest.fixture
def chat(db: Session, spy: SpyLLM) -> Iterator[TestClient]:
    with _client(db, spy) as c:
        yield c


@pytest.fixture
def small_window(monkeypatch):
    monkeypatch.setenv("LLM_MEMORY_MAX_MESSAGES", "4")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _start(chat: TestClient) -> dict[str, str]:
    return {"X-Session-Token": chat.post(f"{CHAT}/sessions").json()["session_token"]}


def _say(chat: TestClient, headers: dict[str, str], text: str) -> dict:
    r = chat.post(f"{CHAT}/messages", json={"content": text}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# Scénario du cahier des charges : un lycéen aime maths et informatique, hésite entre Prépa et Licence,
# vise l'ingénierie logicielle et préfère une voie pratique et progressive.
SCENARIO = [
    "aslema, 9rit bac maths w jebt 15 de moyenne",
    "nheb el maths w l'informatique barcha ama mouch mitakked bin prepa w licence info",
    "nheb nwalli ingénieur logiciel, ama nheb 7aja pratique w progressive",
    "chnowa tnasa7ni ?",
]


def test_orientation_scenario_carries_context_across_turns(chat, spy):
    headers = _start(chat)
    for text in SCENARIO:
        last = _say(chat, headers, text)

    # Tour 4 : le LLM reçoit les règles, puis les 3 échanges précédents dans l'ordre, puis la question.
    system, *dialogue = spy.calls[-1]
    assert [(m.role, m.content) for m in dialogue] == [
        ("user", SCENARIO[0]), ("assistant", "Réponse 1"),
        ("user", SCENARIO[1]), ("assistant", "Réponse 2"),
        ("user", SCENARIO[2]), ("assistant", "Réponse 3"),
        ("user", SCENARIO[3]),
    ]
    # ... et la mémoire du candidat, construite au fil des tours.
    assert "Section du bac : mathématiques" in system.content
    assert "Moyenne : 15" in system.content
    assert "Centres d'intérêt : informatique, mathématiques" in system.content
    assert "Formations évoquées : Cycle préparatoire intégré, Licence en Informatique" in system.content
    assert "Préférences : formation pratique, parcours progressif" in system.content
    assert "Projet professionnel : ingénieur logiciel" in system.content
    assert "Questions déjà posées : " in system.content
    assert "Arabizi" in system.content  # consigne : répondre en Arabizi

    profile = last["memory"]["profile"]
    assert profile["moyenne"] == "15" and profile["niveau"] == "bachelier"
    assert last["memory"]["turns"] == 4
    assert last["reply"]["sequence"] == 8


def test_long_conversation_keeps_profile_when_messages_leave_the_window(chat, spy, small_window):
    headers = _start(chat)
    _say(chat, headers, "9rit bac info w jebt 13.5 de moyenne")
    for i in range(6):
        _say(chat, headers, f"so2al numero {i} 3al formations")

    system, *dialogue = spy.calls[-1]
    # Fenêtre de 4 messages + le message en cours : le premier message n'est plus dans l'historique...
    assert len(dialogue) == 5
    assert all("13.5" not in m.content for m in dialogue)
    assert dialogue[0].content == "so2al numero 3 3al formations"
    # ... mais la mémoire longue l'a retenu.
    assert "Moyenne : 13.5" in system.content
    assert "Section du bac : informatique" in system.content


def test_language_follows_the_candidate_each_turn(chat, spy):
    headers = _start(chat)
    turns = [
        ("Bonjour, quelles formations proposez-vous ?", "fr", "français"),
        ("شنوة الشروط باش ندخل للبريبا ؟", "tn_darija", "dialecte tunisien en graphie arabe"),
        ("w 9adech el flous mta3ha ?", "arabizi", "Arabizi"),
        ("nheb na3ref les frais d'inscription mta3 cycle ingénieur", "mixed", "code-switching"),
    ]
    for i, (text, lang, instruction) in enumerate(turns):
        body = _say(chat, headers, text)
        assert body["user_message"]["detected_language"] == lang
        assert instruction in spy.calls[i][0].content
    history = chat.get(f"{CHAT}/messages", headers=headers).json()["messages"]
    assert [m["detected_language"] for m in history if m["sender"] == "user"] == ["fr", "tn_darija", "arabizi", "mixed"]
    assert chat.get(f"{CHAT}/memoire", headers=headers).json()["language"] == "mixed"


def test_sequences_stay_contiguous_over_many_turns(chat):
    headers = _start(chat)
    for i in range(10):
        _say(chat, headers, f"question {i}")
    seqs = [m["sequence"] for m in chat.get(f"{CHAT}/messages", headers=headers).json()["messages"]]
    assert seqs == list(range(1, 21))


def test_conversation_resumes_after_restart(db: Session, spy):
    with _client(db, spy) as first:
        headers = _start(first)
        _say(first, headers, "9rit bac maths w jebt 16")
    # Nouvelle instance de l'application (redémarrage) : tout vient de la base.
    other_llm = SpyLLM()
    with _client(db, other_llm) as second:
        body = _say(second, headers, "w chnowa najem na9ra ?")
    system, *dialogue = other_llm.calls[-1]
    assert [m.content for m in dialogue] == ["9rit bac maths w jebt 16", "Réponse 1", "w chnowa najem na9ra ?"]
    assert "Moyenne : 16" in system.content
    assert body["memory"]["turns"] == 2


def test_failed_turn_does_not_break_the_dialogue(chat, spy):
    headers = _start(chat)
    _say(chat, headers, "aslema")
    spy.fail = True
    assert chat.post(f"{CHAT}/messages", json={"content": "9adech el prepa ?"}, headers=headers).status_code == 503
    spy.fail = False
    body = _say(chat, headers, "9adech el prepa ?")
    assert body["user_message"]["sequence"] == 3 and body["memory"]["turns"] == 2
    _, *dialogue = spy.calls[-1]
    assert [m.content for m in dialogue] == ["aslema", "Réponse 1", "9adech el prepa ?"]


def test_llm_profile_extraction_option(db: Session, monkeypatch):
    monkeypatch.setenv("LLM_MEMORY_EXTRACTION", "llm")
    get_settings.cache_clear()
    llm = FakeLLMClient(responses=['{"interets": ["robotique"], "lieu": "Sfax"}', "Ahla !"])
    try:
        with _client(db, llm) as c:
            body = _say(c, _start(c), "nheb nekhdem fel robots fi sfax")
    finally:
        get_settings.cache_clear()
    assert body["memory"]["profile"]["contraintes"] == ["ville : Sfax"]
    assert "robotique" in body["memory"]["profile"]["interets"]
    assert len(llm.calls) == 2  # extraction JSON puis réponse


# ----------------------------------------------------------------------------- vrai LLM (optionnel)
@pytest.mark.llm_live
@pytest.mark.skipif(os.environ.get("LLM_LIVE_TESTS") != "1", reason="LLM_LIVE_TESTS=1 requis (serveur LLM réel)")
def test_live_dialogue_with_real_llm(db: Session):
    get_llm_client.cache_clear()
    llm = get_llm_client()
    with _client(db, llm) as c:
        headers = _start(c)
        replies = [_say(c, headers, text)["reply"]["content"] for text in SCENARIO]
    for text, reply in zip(SCENARIO, replies, strict=True):
        print(f"\nCANDIDAT : {text}\nSMARTCAMPUS : {reply}")
    assert all(replies)
    final = replies[-1].lower()
    assert any(k in final for k in ("prepa", "prépa", "بريبا")) or "licence" in final
    assert detect_language(replies[-1]).language.value in {"arabizi", "mixed", "tn_darija", "fr"}
