"""SA-36 — LLM branché au backend : API /chat (sessions visiteurs, messages, historique, mémoire).

Base PostgreSQL réelle (transaction annulée) ; le LLM est remplacé par FakeLLMClient (aucun réseau)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_token
from app.llm.client import FakeLLMClient, get_llm_client
from app.main import create_app
from app.models import Conversation, Message
from app.services.chat_context import catalogue_context


@pytest.fixture
def llm() -> FakeLLMClient:
    return FakeLLMClient(responder=lambda msgs: "Ahla ! El licence info 3 snin, scolarité 5 900 TND.")


@pytest.fixture
def chat_client(db: Session, llm: FakeLLMClient) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: llm
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session_headers(chat_client: TestClient) -> dict[str, str]:
    r = chat_client.post("/api/v1/chat/sessions")
    assert r.status_code == 201
    return {"X-Session-Token": r.json()["session_token"]}


def test_create_session_stores_only_token_hash(chat_client, db: Session):
    body = chat_client.post("/api/v1/chat/sessions").json()
    conv = db.get(Conversation, body["conversation_id"])
    assert len(body["session_token"]) >= 40
    assert conv.session_token_hash == hash_token(body["session_token"])
    assert body["session_token"] not in conv.session_token_hash
    assert conv.memory == {} and conv.candidate_id is None


def test_send_message_returns_reply_and_persists_turn(chat_client, session_headers, db: Session, llm):
    r = chat_client.post("/api/v1/chat/messages", json={"content": "aslema, 9adech el licence info ?"},
                         headers=session_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reply"]["content"].startswith("Ahla")
    assert body["reply"]["sender"] == "assistant" and body["reply"]["sequence"] == 2
    assert body["user_message"]["detected_language"] == "arabizi" and body["user_message"]["sequence"] == 1
    assert body["model"] == "fake-llm"
    assert body["memory"]["turns"] == 1 and body["memory"]["language"] == "arabizi"
    assert body["memory"]["profile"]["formations_evoquees"] == ["Licence en Informatique"]

    conv = db.get(Conversation, body["conversation_id"])
    rows = db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.sequence)).all()
    assert [(m.sender.value, m.detected_language.value) for m in rows] == [("user", "arabizi"), ("assistant", "arabizi")]
    assert rows[0].language_confidence is not None
    assert conv.last_message_at is not None
    assert conv.memory["tours"] == 1


def test_prompt_contains_rules_catalogue_language_and_message(chat_client, session_headers, llm):
    chat_client.post("/api/v1/chat/messages", json={"content": "شنوة الفورماسيونات اللي فمّا ؟"},
                     headers=session_headers)
    system, *rest = llm.calls[-1]
    assert system.role == "system"
    assert "SmartCampus AI" in system.content and "N'invente jamais" in system.content
    assert "dialecte tunisien en graphie arabe" in system.content
    assert "Licence en Informatique (DEMO)" in system.content and "5 900 TND" in system.content
    assert "Cycle ingénieur Génie Civil" not in system.content  # brouillon : jamais montré au LLM
    assert rest[-1].role == "user" and rest[-1].content == "شنوة الفورماسيونات اللي فمّا ؟"


def test_catalogue_context_from_database(db: Session):
    ctx = catalogue_context(db)
    assert "## IIT" in ctx and "## ISB" in ctx
    assert "Master Marketing digital (DEMO)" in ctx and "hybride" in ctx
    assert "moyenne minimale 12/20" in ctx
    assert "inscription 300 TND" in ctx and "scolarité 7 500 TND" in ctx
    assert "Passerelle : vers Cycle ingénieur Génie Informatique (DEMO)" in ctx
    assert "Ancienne licence archivée" not in ctx
    assert "31/12/2026" in ctx
    assert len(ctx) < 6000


def test_history_and_memory_endpoints(chat_client, session_headers):
    chat_client.post("/api/v1/chat/messages", json={"content": "9rit bac maths w jebt 15"}, headers=session_headers)
    chat_client.post("/api/v1/chat/messages", json={"content": "nheb el robotique"}, headers=session_headers)
    hist = chat_client.get("/api/v1/chat/messages", headers=session_headers).json()
    assert [m["sequence"] for m in hist["messages"]] == [1, 2, 3, 4]
    assert [m["sender"] for m in hist["messages"]] == ["user", "assistant", "user", "assistant"]
    mem = chat_client.get("/api/v1/chat/memoire", headers=session_headers).json()
    assert mem["profile"]["moyenne"] == "15" and mem["profile"]["interets"] == ["robotique"]
    assert mem["asked_questions"] == ["9rit bac maths w jebt 15", "nheb el robotique"]
    assert mem["turns"] == 2


def test_sessions_are_isolated(chat_client, session_headers, llm):
    chat_client.post("/api/v1/chat/messages", json={"content": "9rit bac maths w jebt 15"}, headers=session_headers)
    other = {"X-Session-Token": chat_client.post("/api/v1/chat/sessions").json()["session_token"]}
    chat_client.post("/api/v1/chat/messages", json={"content": "Bonjour"}, headers=other)
    assert len(llm.calls[-1]) == 2  # système + message : rien de l'autre visiteur
    assert "15" not in llm.calls[-1][0].content.split("MÉMOIRE")[1]
    assert chat_client.get("/api/v1/chat/memoire", headers=other).json()["profile"] == {}


def test_llm_unavailable_returns_503_and_persists_nothing(chat_client, session_headers, llm, db: Session):
    llm.fail = True
    r = chat_client.post("/api/v1/chat/messages", json={"content": "Bonjour"}, headers=session_headers)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"
    assert db.scalar(select(func.count()).select_from(Message).join(Conversation)
                     .where(Conversation.session_token_hash == hash_token(session_headers["X-Session-Token"]))) == 0
    llm.fail = False
    ok = chat_client.post("/api/v1/chat/messages", json={"content": "Bonjour"}, headers=session_headers)
    assert ok.status_code == 200 and ok.json()["user_message"]["sequence"] == 1
    assert ok.json()["memory"]["turns"] == 1


def test_empty_llm_answer_gets_fallback(chat_client, session_headers, llm):
    llm.responses = ["<think>...</think>"]
    r = chat_client.post("/api/v1/chat/messages", json={"content": "Bonjour"}, headers=session_headers)
    assert r.json()["reply"]["content"].startswith("Désolé")


@pytest.mark.parametrize(
    ("headers", "payload", "status", "code"),
    [
        ({}, {"content": "Bonjour"}, 422, "validation_error"),
        ({"X-Session-Token": "x" * 43}, {"content": "Bonjour"}, 404, "not_found"),
        ({"X-Session-Token": "court"}, {"content": "Bonjour"}, 422, "validation_error"),
    ],
)
def test_session_errors(chat_client, headers, payload, status, code):
    r = chat_client.post("/api/v1/chat/messages", json=payload, headers=headers)
    assert r.status_code == status and r.json()["error"]["code"] == code


@pytest.mark.parametrize("content", ["", "   ", "x" * 2001])
def test_invalid_message(chat_client, session_headers, content, llm):
    r = chat_client.post("/api/v1/chat/messages", json={"content": content}, headers=session_headers)
    assert r.status_code == 422
    assert llm.calls == []


def test_closed_conversation_is_read_only(chat_client, session_headers, db: Session):
    conv = db.scalars(select(Conversation).where(
        Conversation.session_token_hash == hash_token(session_headers["X-Session-Token"]))).one()
    conv.status = "closed"
    db.flush()
    r = chat_client.post("/api/v1/chat/messages", json={"content": "Bonjour"}, headers=session_headers)
    assert r.status_code == 409
    assert chat_client.get("/api/v1/chat/messages", headers=session_headers).status_code == 200


def test_memory_column_must_be_an_object(db: Session):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError, match="memory_is_object"), db.begin_nested():
        db.execute(text("INSERT INTO conversations (session_token_hash, memory) VALUES (:h, '[]'::jsonb)"),
                   {"h": "a" * 64})


def test_get_llm_client_settings(monkeypatch):
    from app.core.config import get_settings
    from app.llm.client import OpenAICompatibleClient

    get_settings.cache_clear()
    get_llm_client.cache_clear()
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    try:
        assert isinstance(get_llm_client(), FakeLLMClient)
        get_settings.cache_clear()
        get_llm_client.cache_clear()
        monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
        monkeypatch.setenv("LLM_MODEL", "qwen3:8b")
        client = get_llm_client()
        assert isinstance(client, OpenAICompatibleClient) and client.model == "qwen3:8b"
    finally:
        get_settings.cache_clear()
        get_llm_client.cache_clear()
