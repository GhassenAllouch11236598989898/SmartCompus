"""SA-22 — OpenAPI, format d'erreur uniforme, CORS, sécurité JWT et temps de réponse."""

import statistics
import time

import jwt
import pytest

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token, hash_password, hash_token, verify_password

API = "/api/v1/formations"


def test_openapi_documents_catalog_routes(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for path in [API, f"{API}/comparer", f"{API}/{{formation_id}}", f"{API}/{{formation_id}}/tarifs",
                 f"{API}/{{formation_id}}/conditions-admission", f"{API}/{{formation_id}}/archiver"]:
        assert path in paths
    assert set(paths[f"{API}/{{formation_id}}"]) == {"get", "put", "patch"}  # pas de DELETE
    assert "HTTPBearer" in spec["components"]["securitySchemes"]
    assert paths[API]["post"]["security"] == [{"HTTPBearer": []}]
    assert "403" in paths[API]["post"]["responses"]


@pytest.mark.parametrize(("method", "url", "status"), [
    ("get", "/api/v1/inexistant", 404),
    ("get", f"{API}/abc", 422),
    ("delete", f"{API}/1", 405),
])
def test_uniform_error_format(client, method, url, status):
    r = getattr(client, method)(url)
    assert r.status_code == status
    body = r.json()
    assert set(body) == {"error"} and {"code", "message", "details"} == set(body["error"])


def test_validation_errors_do_not_echo_input(client):
    r = client.get(API, params={"taille": "secret-value"})
    assert "secret-value" not in r.text


def test_cors_allows_next_frontend(client):
    r = client.options(API, headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "PATCH"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    r = client.options(API, headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


def test_readiness(client):
    assert client.get("/api/v1/health/ready").json() == {"status": "ok", "database": "up"}


def test_password_hashing():
    h = hash_password("S3cret!")
    assert h.startswith("$2b$") and verify_password("S3cret!", h)
    assert not verify_password("autre", h) and not verify_password("x", "pas-un-hash")
    assert len(hash_token("abc")) == 64


def test_jwt_rules():
    token = create_access_token(7, ["admin"])
    assert decode_access_token(token)["sub"] == "7"
    settings = get_settings()
    refresh = jwt.encode({"sub": "7", "exp": 9999999999, "iat": 0, "type": "refresh"}, settings.jwt_secret_key)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(refresh)
    forged = jwt.encode({"sub": "7", "exp": 9999999999, "iat": 0, "type": "access"}, "mauvaise-cle-" * 4)
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_non_numeric_subject_rejected(client):
    settings = get_settings()
    token = jwt.encode({"sub": "abc", "exp": 9999999999, "iat": 0, "type": "access"}, settings.jwt_secret_key)
    assert client.post(API, json={}, headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("path", [API, f"{API}?q=informatique", f"{API}/comparer"])
def test_response_times(client, program_id, path):
    if path.endswith("comparer"):
        path += f"?ids={program_id('IIT-LIC-INFO')},{program_id('IIT-ING-GI')}"
    client.get(path)  # préchauffage
    durations = []
    for _ in range(10):
        start = time.perf_counter()
        r = client.get(path)
        durations.append((time.perf_counter() - start) * 1000)
        assert r.status_code == 200 and float(r.headers["x-response-time-ms"]) >= 0
    # Budget : p50 < 150 ms et max < 500 ms sur la base de démo (TestClient en local).
    assert statistics.median(durations) < 150, durations
    assert max(durations) < 500, durations
