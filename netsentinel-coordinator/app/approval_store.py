import sqlite3
import os
import datetime
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "approvals.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
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

# Initialize database on import
init_db()

def create_pending_approval(action_summary: str, risk_level: str, incident_id: Optional[str] = None) -> str:
    import uuid
    approval_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cursor.execute(
        "INSERT INTO approvals (approval_id, incident_id, action_summary, risk_level, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (approval_id, incident_id, action_summary, risk_level, "pending", created_at)
    )
    conn.commit()
    conn.close()
    return approval_id

def resolve_approval(approval_id: str, decision: str, decided_by: str) -> bool:
    # decision should be 'approve' or 'deny'
    # We will map it to 'approved' or 'denied' in status field
    status = "approved" if decision in ("approve", "approved") else "denied"
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    decided_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cursor.execute(
        "UPDATE approvals SET status = ?, decided_at = ?, decided_by = ? WHERE approval_id = ?",
        (status, decided_at, decided_by, approval_id)
    )
    conn.commit()
    # Check if a row was updated
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def get_pending_approvals() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM approvals WHERE status = 'pending'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_approval_status(approval_id: str) -> Optional[str]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM approvals WHERE approval_id = ?", (approval_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
