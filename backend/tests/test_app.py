"""Tests de démarrage et de contrat HTTP minimal."""

from fastapi.testclient import TestClient
from app.main import create_app

client = TestClient(create_app())


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "smartcampus-backend"}


def test_api_documentation():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]


def test_unknown_endpoint():
    response = client.get("/api/v1/not-found")
    assert response.status_code == 404
