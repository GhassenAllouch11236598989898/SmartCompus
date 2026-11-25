"""SA-28 — Tests de l'authentification et de la gestion des rôles."""

from sqlalchemy import select

from app.models import Candidate, User

DEMO_PASSWORD = "Demo2026!"
NEW_USER = {"email": "Nour.Test@Example.com", "password": "MotDePasse123", "first_name": "Nour", "last_name": "Test"}


def _register(client, **overrides) -> dict:
    return client.post("/api/v1/auth/register", json={**NEW_USER, **overrides}).json()


def test_register_creates_candidate_account(client, db):
    r = client.post("/api/v1/auth/register", json=NEW_USER)
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"] and body["token_type"] == "bearer"
    assert body["user"]["email"] == "nour.test@example.com"
    assert body["user"]["roles"] == ["candidate"]

    user = db.get(User, body["user"]["id"])
    assert user.password_hash != NEW_USER["password"]
    assert user.password_hash.startswith("$2")
    assert db.scalars(select(Candidate).where(Candidate.user_id == user.id)).one().first_name == "Nour"


def test_register_duplicate_email_is_rejected(client):
    _register(client)
    r = client.post("/api/v1/auth/register", json={**NEW_USER, "email": "nour.test@example.com"})
    assert r.status_code == 409


def test_register_validates_input(client):
    assert client.post("/api/v1/auth/register", json={**NEW_USER, "password": "court"}).status_code == 422
    assert client.post("/api/v1/auth/register", json={**NEW_USER, "email": "pas-un-email"}).status_code == 422


def test_login_success_and_me(client):
    _register(client)
    r = client.post("/api/v1/auth/login", json={"email": "nour.test@example.com", "password": "MotDePasse123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["roles"] == ["candidate"]


def test_login_wrong_password_or_unknown_email(client):
    _register(client)
    bad = client.post("/api/v1/auth/login", json={"email": "nour.test@example.com", "password": "mauvais"})
    unknown = client.post("/api/v1/auth/login", json={"email": "inconnu@example.com", "password": "MotDePasse123"})
    assert bad.status_code == 401 and unknown.status_code == 401
    assert bad.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_login_demo_admin(client):
    r = client.post("/api/v1/auth/login", json={"email": "admin@demo.smartcampus.invalid", "password": DEMO_PASSWORD})
    assert r.status_code == 200
    assert "admin" in r.json()["user"]["roles"]


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer faux"}).status_code == 401


def test_candidate_cannot_change_roles(client):
    body = _register(client)
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    r = client.put(f"/api/v1/auth/users/{body['user']['id']}/roles", json={"roles": ["admin"]}, headers=headers)
    assert r.status_code == 403


def test_admin_can_change_roles(client, auth):
    body = _register(client)
    r = client.put(
        f"/api/v1/auth/users/{body['user']['id']}/roles",
        json={"roles": ["candidate", "responsable_entretien"]},
        headers=auth("admin"),
    )
    assert r.status_code == 200
    assert r.json()["roles"] == ["candidate", "responsable_entretien"]


def test_admin_cannot_remove_own_admin_role(client, auth, user_by_email):
    admin = user_by_email("admin")
    r = client.put(f"/api/v1/auth/users/{admin.id}/roles", json={"roles": ["candidate"]}, headers=auth("admin"))
    assert r.status_code == 422
    