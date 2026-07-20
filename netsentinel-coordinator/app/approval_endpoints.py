import os
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional
from app.approval_store import get_pending_approvals, resolve_approval, get_approval_history

router = APIRouter()

API_KEY_ENV_VAR = "APPROVAL_API_KEY"

def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verifies that the request carries a valid API key if APPROVAL_API_KEY is configured."""
    required_key = os.environ.get(API_KEY_ENV_VAR)
    if required_key:
        if not x_api_key or x_api_key != required_key:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing X-API-Key header.")
    return x_api_key

class DecisionPayload(BaseModel):
    decision: str  # "approve" or "deny"
    decided_by: str

@router.get("/approvals/pending")
def list_pending():
    """List all pending human approvals."""
    return get_pending_approvals()

@router.get("/approvals/history")
def list_history(limit: int = 50):
    """List resolved/denied/timed-out human approvals for audit log inspection."""
    return get_approval_history(limit=limit)

@router.post("/approvals/{approval_id}/decide", dependencies=[Depends(verify_api_key)])
def decide(approval_id: str, payload: DecisionPayload):
    """Submit a decision (approve/deny) for a pending approval."""
    if payload.decision not in ("approve", "deny"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'deny'")
    
    success = resolve_approval(approval_id, payload.decision, payload.decided_by)
    if not success:
        raise HTTPException(status_code=404, detail="Approval ID not found or already resolved")
    return {"status": "success"}


