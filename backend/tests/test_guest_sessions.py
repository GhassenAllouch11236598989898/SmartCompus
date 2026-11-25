"""SA-25 — Tests des sessions visiteurs."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_token
from app.models import Conversation


def test_create_session_returns_token(client, db):
    r = client.post("/api/v1/sessions")
    assert r.status_code == 201
    body = r.json()
    assert body["session_token"] and body["conversation_id"] and body["expires_at"]
    conv = db.get(Conversation, body["conversation_id"])
    assert conv.session_token_hash == hash_token(body["session_token"])
    assert conv.candidate_id is None
    assert conv.status.value == "active"


def test_same_token_finds_same_session(client):
    created = client.post("/api/v1/sessions").json()
    r = client.get("/api/v1/sessions/me", headers={"X-Session-Token": created["session_token"]})
    assert r.status_code == 200
    assert r.json()["conversation_id"] == created["conversation_id"]


def test_two_visitors_get_different_sessions(client):
    a = client.post("/api/v1/sessions").json()
    b = client.post("/api/v1/sessions").json()
    assert a["session_token"] != b["session_token"]
    assert a["conversation_id"] != b["conversation_id"]


def test_missing_or_unknown_token_is_rejected(client):
    assert client.get("/api/v1/sessions/me").status_code == 401
    assert client.get("/api/v1/sessions/me", headers={"X-Session-Token": "faux"}).status_code == 401


def test_expired_session_is_closed(client, db):
    created = client.post("/api/v1/sessions").json()
    conv = db.scalars(
        select(Conversation).where(Conversation.session_token_hash == hash_token(created["session_token"]))
    ).one()
    conv.started_at = datetime.now(UTC) - timedelta(days=30)
    db.commit()
    r = client.get("/api/v1/sessions/me", headers={"X-Session-Token": created["session_token"]})
    assert r.status_code == 401
    db.refresh(conv)
    assert conv.status.value == "closed"