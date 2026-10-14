import os
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["provider"] == "e2b"


def test_execution_requires_token(monkeypatch):
    monkeypatch.setenv("KZ_SANDBOX_RUNNER_TOKEN", "test-secret")
    response = client.post("/v1/execute", json={"files": [{"path": "main.py", "content": "print(1)"}]})
    assert response.status_code == 401


def test_rejects_env_files(monkeypatch):
    monkeypatch.setenv("KZ_SANDBOX_RUNNER_TOKEN", "test-secret")
    response = client.post(
        "/v1/execute",
        headers={"Authorization": "Bearer test-secret"},
        json={"files": [{"path": ".env", "content": "SECRET=x"}]},
    )
    assert response.status_code == 400


def test_rejects_traversal(monkeypatch):
    monkeypatch.setenv("KZ_SANDBOX_RUNNER_TOKEN", "test-secret")
    response = client.post(
        "/v1/execute",
        headers={"Authorization": "Bearer test-secret"},
        json={"files": [{"path": "../main.py", "content": "print(1)"}]},
    )
    assert response.status_code == 400


def test_rejects_shell_command(monkeypatch):
    monkeypatch.setenv("KZ_SANDBOX_RUNNER_TOKEN", "test-secret")
    response = client.post(
        "/v1/execute",
        headers={"Authorization": "Bearer test-secret"},
        json={"files": [{"path": "main.py", "content": "print(1)"}], "command": ["python", "-c", "print(1)"]},
    )
    assert response.status_code == 400
