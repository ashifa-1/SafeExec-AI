"""API Integration and Contract Tests for SafeExec AI."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Verify GET /health returns strictly {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_runs_includes_seeded_sandbox():
    """Verify GET /api/runs returns stored runs and includes seeded sbx-seeddemo1."""
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1
    # Check seeded sandbox presence
    sandbox_names = [r["sandbox_name"] for r in runs]
    assert "sbx-seeddemo1" in sandbox_names, "Seeded sandbox sbx-seeddemo1 must be present in GET /api/runs"


def test_post_runs_valid_celesto_sandbox():
    """Verify POST /api/runs accepts valid celesto_sandbox run record."""
    payload = {
        "run_id": "run-test-unit-001",
        "sandbox_name": "sbx-unittst01",
        "problem_id": "problem-fib-calc",
        "state": "created",
        "execution_target": "celesto_sandbox"
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["run_id"] == "run-test-unit-001"
    assert data["sandbox_name"] == "sbx-unittst01"
    assert data["execution_target"] == "celesto_sandbox"


def test_post_runs_rejects_host_target():
    """Verify POST /api/runs strictly rejects host as execution target with HTTP 400."""
    payload = {
        "run_id": "run-test-host-reject",
        "sandbox_name": "sbx-hostfail1",
        "problem_id": "problem-host-forbidden",
        "state": "created",
        "execution_target": "host"
    }
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 422 or response.status_code == 400


def test_execute_endpoint():
    """Verify POST /api/execute runs code inside an isolated Celesto sandbox."""
    payload = {
        "code": "print('Test execution endpoint')",
        "language": "python"
    }
    response = client.post("/api/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Test execution endpoint" in data["stdout"]
    assert data["sandbox_name"].startswith("sbx-")


def test_agent_run_endpoint():
    """Verify POST /api/agent/run dispatches coding task and records output."""
    payload = {
        "task": "Compute primes up to 20",
        "problem_id": "problem-prime-test"
    }
    response = client.post("/api/agent/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"].startswith("run-")
    assert len(data["steps"]) >= 1
    assert data["success"] is True


def test_get_reports_endpoint():
    """Verify GET /api/reports returns all parsed submission report objects."""
    response = client.get("/api/reports")
    assert response.status_code == 200
    data = response.json()
    assert "problem" in data
    assert "capabilities" in data
    assert "lifecycle" in data
    assert "reliability" in data
    assert "containment" in data
    assert "failure_policy" in data
    assert "concurrency" in data
    assert "postmortem" in data
