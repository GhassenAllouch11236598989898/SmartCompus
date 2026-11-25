"""SA-26 — Tests de la mémoire temporaire des conversations."""

from app.models import Conversation
from app.models.applications import MessageSender
from app.services import memory


def _new_session(client) -> dict:
    created = client.post("/api/v1/sessions").json()
    return {"X-Session-Token": created["session_token"]}


def test_post_message_is_saved_with_sequence(client):
    headers = _new_session(client)
    r1 = client.post("/api/v1/sessions/me/messages", json={"content": "Bonjour"}, headers=headers)
    r2 = client.post("/api/v1/sessions/me/messages", json={"content": "Je suis en bac info"}, headers=headers)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["sequence"] == 1
    assert r2.json()["sequence"] == 2
    assert r2.json()["sender"] == "user"


def test_history_returns_messages_in_order(client):
    headers = _new_session(client)
    for text in ["un", "deux", "trois"]:
        client.post("/api/v1/sessions/me/messages", json={"content": text}, headers=headers)
    r = client.get("/api/v1/sessions/me/messages", headers=headers)
    assert r.status_code == 200
    assert [m["content"] for m in r.json()["messages"]] == ["un", "deux", "trois"]


def test_history_limit_keeps_latest_messages(client):
    headers = _new_session(client)
    for i in range(5):
        client.post("/api/v1/sessions/me/messages", json={"content": f"m{i}"}, headers=headers)
    r = client.get("/api/v1/sessions/me/messages?limit=2", headers=headers)
    assert [m["content"] for m in r.json()["messages"]] == ["m3", "m4"]


def test_sessions_do_not_share_memory(client):
    a, b = _new_session(client), _new_session(client)
    client.post("/api/v1/sessions/me/messages", json={"content": "secret A"}, headers=a)
    r = client.get("/api/v1/sessions/me/messages", headers=b)
    assert r.json()["messages"] == []


def test_message_requires_valid_session(client):
    assert client.post("/api/v1/sessions/me/messages", json={"content": "x"}).status_code == 401
    r = client.post("/api/v1/sessions/me/messages", json={"content": ""}, headers=_new_session(client))
    assert r.status_code == 422


def test_message_updates_last_activity(client, db):
    headers = _new_session(client)
    conv_id = client.get("/api/v1/sessions/me", headers=headers).json()["conversation_id"]
    client.post("/api/v1/sessions/me/messages", json={"content": "salut"}, headers=headers)
    assert db.get(Conversation, conv_id).last_message_at is not None


def test_llm_history_format(client, db):
    headers = _new_session(client)
    conv_id = client.get("/api/v1/sessions/me", headers=headers).json()["conversation_id"]
    conv = db.get(Conversation, conv_id)
    memory.add_message(db, conv, MessageSender.user, "Quelles formations en IA ?")
    memory.add_message(db, conv, MessageSender.assistant, "Le master IA de l'IIT.")
    assert memory.get_llm_history(db, conv) == [
        {"role": "user", "content": "Quelles formations en IA ?"},
        {"role": "assistant", "content": "Le master IA de l'IIT."},
    ]