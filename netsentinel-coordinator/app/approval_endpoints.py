from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.approval_store import get_pending_approvals, resolve_approval

router = APIRouter()

class DecisionPayload(BaseModel):
    decision: str  # "approve" or "deny"
    decided_by: str

@router.get("/approvals/pending")
def list_pending():
    """List all pending human approvals."""
    return get_pending_approvals()

@router.post("/approvals/{approval_id}/decide")
def decide(approval_id: str, payload: DecisionPayload):
    """Submit a decision (approve/deny) for a pending approval."""
    if payload.decision not in ("approve", "deny"):
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'deny'")
    
    success = resolve_approval(approval_id, payload.decision, payload.decided_by)
    if not success:
        raise HTTPException(status_code=404, detail="Approval ID not found or already resolved")
    return {"status": "success"}
