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
