# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from typing import List

from pydantic import BaseModel, Field

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.tools import MCPToolset
from mcp.client.stdio import StdioServerParameters

from app.memory_store import query_past_incidents, save_incident_resolution

# Use AI Studio (API Key) instead of Vertex AI (ADC)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

def request_human_approval(action_summary: str, risk_level: str) -> bool:
    """Requests human approval before executing sensitive operations."""
    from app.approval_store import create_pending_approval, get_approval_status
    import time
    
    # Check if we are running in a test environment that mocks the approval response
    if os.environ.get("INTEGRATION_TEST_MOCK_APPROVAL") == "TRUE":
        mock_decision = os.environ.get("INTEGRATION_TEST_MOCK_DECISION", "approved")
        print(f"[MOCK APPROVAL] Action: {action_summary}. Decision: {mock_decision}")
        return mock_decision == "approved"

    approval_id = create_pending_approval(action_summary, risk_level)
    print(f"[PENDING APPROVAL] Agent requested permission to execute: {action_summary}. Risk Level: {risk_level}. Approval ID: {approval_id}")
    
    # Poll database for status update (max 60 seconds)
    timeout = 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        status = get_approval_status(approval_id)
        if status == "approved":
            print(f"[APPROVED] Approval {approval_id} has been approved.")
            return True
        elif status == "denied":
            print(f"[DENIED] Approval {approval_id} has been denied.")
            return False
        time.sleep(1)
        
    print(f"[TIMEOUT] Approval {approval_id} timed out after {timeout} seconds.")
    return False

class IncidentAssessment(BaseModel):
    severity: str = Field(description="The severity of the incident.")
    suspected_component: str = Field(description="The suspected faulty component.")
    recommended_agent_routing: List[str] = Field(description="List of agents to route to.")
    immediate_action_required: bool = Field(description="Whether immediate action is needed.")

infra_mcp_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command=sys.executable,
        args=["infra_mcp_server.py"],
    )
)

log_analyzer = Agent(
    name="log_analyzer",
    model=Gemini(
        model="gemini-2.0-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a specialized Log Analyzer Agent. Use your tools to fetch and analyze logs and network latency.",
    tools=[infra_mcp_toolset],
)

netsentinel_coordinator = Agent(
    name="netsentinel_coordinator",
    model=Gemini(
        model="gemini-2.0-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a lead Site Reliability Engineer for an infrastructure monitoring platform.
You must NEVER output a final remediation plan or recommend an infrastructure change without first calling the `request_human_approval` tool. If the human denies the request, you must abort the operation and log a security constraint violation.
Before routing an alert to a sub-agent, you must always query your past incident memory using key terms from the alert. If a definitive past resolution is found, include it in your structured output and skip routing to a sub-agent.
If no past resolution is found, use your sub_agents to investigate it. If you formulate a new resolution based on your investigation, you MUST use the `save_incident_resolution` tool to store it for future incidents.
After investigating and saving, you MUST output a structured JSON response assessing the incident.
The JSON must strictly follow this structure:
{
  "severity": "string",
  "suspected_component": "string",
  "recommended_agent_routing": ["list", "of", "agents"],
  "immediate_action_required": true
}""",
    sub_agents=[log_analyzer], # Note: ADK uses sub_agents instead of can_handoff_to
    tools=[query_past_incidents, save_incident_resolution, request_human_approval],
)

app = App(
    root_agent=netsentinel_coordinator,
    name="app",
)

root_agent = netsentinel_coordinator

