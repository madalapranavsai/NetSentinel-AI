import os
import sqlite3
import pytest
import time
from threading import Thread
from app.approval_store import (
    create_pending_approval,
    resolve_approval,
    get_pending_approvals,
    get_approval_status,
)
from app.agent import request_human_approval

@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    # Set a temporary database file for the test
    temp_db = tmp_path / "approvals.db"
    monkeypatch.setattr("app.approval_store.DB_FILE", str(temp_db))
    
    # Initialize the temp DB structure
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approvals (
            approval_id TEXT PRIMARY KEY,
            incident_id TEXT,
            action_summary TEXT,
            risk_level TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            decided_at TEXT,
            decided_by TEXT
        )
    """)
    conn.commit()
    conn.close()
    yield

def test_create_and_resolve_approval():
    # 1. Create approval
    app_id = create_pending_approval("Scale up replica", "HIGH", "INC-001")
    assert app_id is not None
    
    # 2. Check pending list
    pending = get_pending_approvals()
    assert len(pending) == 1
    assert pending[0]["approval_id"] == app_id
    assert pending[0]["action_summary"] == "Scale up replica"
    assert pending[0]["risk_level"] == "HIGH"
    assert pending[0]["incident_id"] == "INC-001"
    assert pending[0]["status"] == "pending"
    
    # 3. Resolve approval (approve)
    resolved = resolve_approval(app_id, "approve", "operator-1")
    assert resolved is True
    
    # 4. Check status
    assert get_approval_status(app_id) == "approved"
    assert len(get_pending_approvals()) == 0

def test_resolve_approval_deny():
    app_id = create_pending_approval("Delete pods", "CRITICAL")
    resolved = resolve_approval(app_id, "deny", "operator-2")
    assert resolved is True
    assert get_approval_status(app_id) == "denied"

def test_request_human_approval_polls_and_approves():
    # Define a background thread function to approve the request after 1 second
    def delayed_resolve():
        time.sleep(1)
        pending = get_pending_approvals()
        if pending:
            resolve_approval(pending[0]["approval_id"], "approve", "operator-bg")

    thread = Thread(target=delayed_resolve)
    thread.start()
    
    # This should block for ~1 second and then return True
    result = request_human_approval("Restart payment service", "LOW")
    assert result is True
    thread.join()

def test_request_human_approval_polls_and_denies():
    # Define a background thread function to deny the request after 1 second
    def delayed_resolve():
        time.sleep(1)
        pending = get_pending_approvals()
        if pending:
            resolve_approval(pending[0]["approval_id"], "deny", "operator-bg")

    thread = Thread(target=delayed_resolve)
    thread.start()
    
    # This should block for ~1 second and then return False
    result = request_human_approval("Restart database service", "HIGH")
    assert result is False
    thread.join()

def test_request_human_approval_timeout(monkeypatch):
    # Mock time.time to simulate rapid passage of time
    time_calls = [100.0, 170.0]
    def mock_time():
        if time_calls:
            return time_calls.pop(0)
        return 200.0
    
    monkeypatch.setattr(time, "time", mock_time)
    monkeypatch.setattr(time, "sleep", lambda x: None)
    
    result = request_human_approval("Restart database service", "HIGH")
    assert result is False

def test_approval_endpoint_api_key_auth(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    
    client = TestClient(app)
    app_id = create_pending_approval("Restart app", "LOW")
    
    # 1. Without API key configured, request succeeds
    monkeypatch.delenv("APPROVAL_API_KEY", raising=False)
    resp = client.post(f"/approvals/{app_id}/decide", json={"decision": "approve", "decided_by": "op"})
    assert resp.status_code == 200

    # 2. With APPROVAL_API_KEY configured, request without X-API-Key fails (401)
    app_id2 = create_pending_approval("Restart database", "HIGH")
    monkeypatch.setenv("APPROVAL_API_KEY", "secret-key-123")
    resp_unauth = client.post(f"/approvals/{app_id2}/decide", json={"decision": "approve", "decided_by": "op"})
    assert resp_unauth.status_code == 401
    assert "Unauthorized" in resp_unauth.json()["detail"]

    # 3. With APPROVAL_API_KEY configured, request with valid X-API-Key succeeds
    resp_auth = client.post(
        f"/approvals/{app_id2}/decide",
        json={"decision": "approve", "decided_by": "op"},
        headers={"X-API-Key": "secret-key-123"}
    )
    assert resp_auth.status_code == 200

def test_get_approval_history():
    from app.approval_store import get_approval_history
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    
    # 1. Create and resolve approvals
    app_id1 = create_pending_approval("Flush redis cache", "LOW")
    app_id2 = create_pending_approval("Scale k8s cluster", "HIGH")
    
    resolve_approval(app_id1, "approve", "sre-alice")
    resolve_approval(app_id2, "deny", "sre-bob")

    # 2. Query store function directly
    history = get_approval_history(limit=10)
    assert len(history) >= 2
    statuses = [item["status"] for item in history]
    assert "approved" in statuses
    assert "denied" in statuses

    # 3. Test HTTP endpoint GET /approvals/history
    resp = client.get("/approvals/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


