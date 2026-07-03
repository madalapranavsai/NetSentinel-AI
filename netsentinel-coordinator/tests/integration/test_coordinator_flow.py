import json
import os
import pytest
from app.agent import app as adk_app, IncidentAssessment
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

mock_alert_1 = {
    "incident_id": "INC-84729",
    "timestamp": "2026-06-24T12:50:00Z",
    "cluster": "prod-cluster-us-east1",
    "namespace": "payment-processing",
    "pod": "payment-worker-7b94c8d-abcde",
    "container": "worker",
    "reason": "OOMKilled",
    "message": "Back-off restarting failed container",
    "status": "CrashLoopBackOff",
    "resource_limits": {
        "memory": "512Mi"
    },
    "current_usage": {
        "memory": "512Mi"
    }
}

@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY is not set")
@pytest.mark.asyncio
async def test_coordinator_flow_success(monkeypatch):
    # Mock approvals to auto-approve in agent tool
    monkeypatch.setenv("INTEGRATION_TEST_MOCK_APPROVAL", "TRUE")
    monkeypatch.setenv("INTEGRATION_TEST_MOCK_DECISION", "approved")
    
    session_service = InMemorySessionService()
    runner = Runner(
        app=adk_app,
        session_service=session_service,
        auto_create_session=True
    )
    
    prompt = f"Please assess this infrastructure alert:\n\n{json.dumps(mock_alert_1, indent=2)}"
    new_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    
    final_text = ""
    async for event in runner.run_async(user_id="test_user", session_id="test_session", new_message=new_message):
        event_type = type(event).__name__
        if event_type != "LlmChunkEvent":
            if hasattr(event, "parts"):
                for part in event.parts:
                    if hasattr(part, "text") and part.text:
                        final_text += part.text

    # Extract JSON content
    clean_text = final_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    if clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
        
    parsed_json = json.loads(clean_text)
    
    # Assert keys exist
    assert "severity" in parsed_json
    assert "suspected_component" in parsed_json
    assert "recommended_agent_routing" in parsed_json
    assert "immediate_action_required" in parsed_json
    
    # Assert Types/Schema
    assessment = IncidentAssessment(**parsed_json)
    assert isinstance(assessment.severity, str)
    assert isinstance(assessment.suspected_component, str)
    assert isinstance(assessment.recommended_agent_routing, list)
    assert isinstance(assessment.immediate_action_required, bool)
