"""SA-29 — Tests du rattachement d'une conversation invitée à un compte candidat."""

from sqlalchemy import select

from app.models import Candidate, Conversation

PASSWORD = "MotDePasse123"


def _guest_with_messages(client, *texts: str) -> tuple[dict, int]:
    created = client.post("/api/v1/sessions").json()
    headers = {"X-Session-Token": created["session_token"]}
    for text in texts:
        client.post("/api/v1/sessions/me/messages", json={"content": text}, headers=headers)
    return headers, created["conversation_id"]


def _register(client, email: str, headers: dict | None = None):
    payload = {"email": email, "password": PASSWORD, "first_name": "Test", "last_name": "Candidat"}
    return client.post("/api/v1/auth/register", json=payload, headers=headers or {})


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_attaches_guest_conversation(client, db):
    guest, conv_id = _guest_with_messages(client, "Bonjour", "Je suis en bac info")
    r = _register(client, "sa29.register@example.com", guest)
    assert r.status_code == 201
    assert r.json()["attached_conversation_id"] == conv_id

    candidate = db.scalars(select(Candidate).where(Candidate.user_id == r.json()["user"]["id"])).one()
    conv = db.get(Conversation, conv_id)
    db.refresh(conv)
    assert conv.candidate_id == candidate.id
    assert conv.attached_at is not None


def test_candidate_finds_history_after_signup(client):
    guest, conv_id = _guest_with_messages(client, "un", "deux", "trois")
    token = _register(client, "sa29.history@example.com", guest).json()["access_token"]
    r = client.get("/api/v1/auth/me/conversations", headers=_bearer(token))
    assert r.status_code == 200
    assert r.json()[0]["conversation_id"] == conv_id
    assert r.json()[0]["message_count"] == 3


def test_login_attaches_guest_conversation(client):
    _register(client, "sa29.login@example.com")
    guest, conv_id = _guest_with_messages(client, "Je reviens sans être connecté")
    r = client.post(
        "/api/v1/auth/login", json={"email": "sa29.login@example.com", "password": PASSWORD}, headers=guest
    )
    assert r.status_code == 200
    assert r.json()["attached_conversation_id"] == conv_id


def test_register_without_session_attaches_nothing(client):
    r = _register(client, "sa29.none@example.com")
    assert r.status_code == 201
    assert r.json()["attached_conversation_id"] is None


def test_invalid_session_token_does_not_block_login(client):
    _register(client, "sa29.badtoken@example.com")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "sa29.badtoken@example.com", "password": PASSWORD},
        headers={"X-Session-Token": "faux"},
    )
    assert r.status_code == 200
    assert r.json()["attached_conversation_id"] is None


def test_explicit_attach_is_idempotent(client):
    token = _register(client, "sa29.explicit@example.com").json()["access_token"]
    guest, conv_id = _guest_with_messages(client, "salut")
    headers = {**_bearer(token), **guest}
    first = client.post("/api/v1/auth/me/conversations/attach", headers=headers)
    second = client.post("/api/v1/auth/me/conversations/attach", headers=headers)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["conversation_id"] == second.json()["conversation_id"] == conv_id
    assert first.json()["message_count"] == 1


def test_conversation_of_another_candidate_is_refused(client):
    guest, _ = _guest_with_messages(client, "à moi")
    _register(client, "sa29.owner@example.com", guest)
    other = _register(client, "sa29.other@example.com").json()["access_token"]
    r = client.post("/api/v1/auth/me/conversations/attach", headers={**_bearer(other), **guest})
    assert r.status_code == 409


def test_attach_requires_account_and_session(client, auth):
    guest, _ = _guest_with_messages(client, "x")
    assert client.post("/api/v1/auth/me/conversations/attach", headers=guest).status_code == 401
    token = _register(client, "sa29.nosession@example.com").json()["access_token"]
    assert client.post("/api/v1/auth/me/conversations/attach", headers=_bearer(token)).status_code == 401
    r = client.post("/api/v1/auth/me/conversations/attach", headers={**auth("admin"), **guest})
    assert r.status_code == 422