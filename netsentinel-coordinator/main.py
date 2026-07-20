import json
import os
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import app as adk_app, IncidentAssessment
from app.security_eval import validate_alert_payload

app = FastAPI(
    title="NetSentinel AI",
    description="Multi-Agent Infrastructure Remediation API",
    version="1.0.0"
)

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    origins = ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.approval_endpoints import router as approval_router
app.include_router(approval_router)

@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
def read_dashboard():
    """Serve the approvals dashboard."""
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r") as f:
            return f.read()
    return "Dashboard HTML file not found."


# 1. Define the Pydantic schema for the incoming alert payload
class AlertPayload(BaseModel):
    alert_id: Optional[str] = None
    source: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    target_resource: Optional[str] = None
    namespace: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    description: Optional[str] = None

# Initialize the InMemorySessionService to maintain state across agent runs
session_service = InMemorySessionService()

# 2. Create an asynchronous POST endpoint
@app.post("/api/v1/alerts", response_model=IncidentAssessment)
async def process_alert(alert: AlertPayload):
    # Convert Pydantic object to a dictionary for our scanner and prompt
    payload_dict = alert.model_dump(exclude_none=True)
    
    # 3. Pass payload through the security scanner first!
    try:
        validate_alert_payload(payload_dict)
    except ValueError as e:
        # Immediately reject the HTTP request with a 403 Forbidden
        raise HTTPException(status_code=403, detail=f"Security Blocked: {str(e)}")

    # 4. Initialize the ADK Runner with our Coordinator Agent
    runner = Runner(
        app=adk_app,
        session_service=session_service,
        auto_create_session=True
    )
    
    # Formulate the incoming message
    prompt = f"Please assess this infrastructure alert:\n\n{json.dumps(payload_dict, indent=2)}"
    new_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    
    # Execute the agent and capture its output
    final_text = ""
    async for event in runner.run_async(user_id="api_user", session_id="api_session", new_message=new_message):
        event_type = type(event).__name__
        
        # We ignore LlmChunkEvent and look for the final completed Message events
        if event_type != "LlmChunkEvent":
            if hasattr(event, "parts"):
                for part in event.parts:
                    if hasattr(part, "text") and part.text:
                        final_text += part.text

    # 5. Extract the structured JSON from the agent's text response
    try:
        # Strip potential markdown formatting that the LLM might have wrapped the JSON in
        clean_text = final_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        parsed_json = json.loads(clean_text)
        
        # Parse into the IncidentAssessment Pydantic object
        assessment = IncidentAssessment(**parsed_json)
        
        # Return the Pydantic object natively (FastAPI automatically converts this to an HTTP JSON response)
        return assessment
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Agent failed to generate valid JSON.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Agent Error: {str(e)}")

# Health check endpoint for Cloud Run
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
