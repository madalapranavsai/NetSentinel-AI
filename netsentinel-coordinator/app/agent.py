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
from typing import List

from pydantic import BaseModel, Field

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Use AI Studio (API Key) instead of Vertex AI (ADC)
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"

class IncidentAssessment(BaseModel):
    severity: str = Field(description="The severity of the incident.")
    suspected_component: str = Field(description="The suspected component causing the issue.")
    recommended_agent_routing: List[str] = Field(description="List of recommended agents to route to. Choose from: Log Agent, Network Agent, Security Agent, Infra Agent.")
    immediate_action_required: bool = Field(description="Whether immediate action is required.")

netsentinel_coordinator = Agent(
    name="netsentinel_coordinator",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a lead Site Reliability Engineer for an infrastructure monitoring platform. When you receive an alert payload, analyze it and output a structured JSON response assessing the incident.",
    output_schema=IncidentAssessment,
)

app = App(
    root_agent=netsentinel_coordinator,
    name="app",
)
