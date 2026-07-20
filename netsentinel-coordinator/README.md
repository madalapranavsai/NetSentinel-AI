# NetSentinel AI

NetSentinel AI is a production-grade, multi-agent AI infrastructure remediator built using the **Google Agent Development Kit (ADK)** and **FastAPI**. It operates as an autonomous Site Reliability Engineer (SRE) to catch webhook alerts from monitoring tools (like Datadog or Prometheus), query system logs via MCP, check historical incident memories, and automatically generate infrastructure remediation plans with human-in-the-loop approval.

---

## Features

- **Human-in-the-Loop Approvals**: Programmatically holds sensitive agent actions in a pending state, allowing operators to inspect, approve, or deny actions via a sleek, real-time glassmorphic SRE operator dashboard.
- **Audit & Compliance History**: Complete audit log tracking (`GET /approvals/history`) storing decision timestamp, resolution status (`APPROVED`, `DENIED`, `TIMED_OUT`), and operator identity (`decided_by`).
- **High-Risk Confirmation Modals**: Explicit modal confirmation prompts for `HIGH` and `CRITICAL` risk operations before execution on live infrastructure.
- **Multi-Agent Orchestration**: Lead SRE `Coordinator` agent orchestrates specialized sub-agents (e.g., `Log Analyzer`) built on Gemini models.
- **FastMCP Tooling Integration**: Infrastructure tools (`get_kubernetes_pod_logs`, `check_network_latency`) served via a dedicated Model Context Protocol (MCP) STDIO server (`infra_mcp_server.py`).
- **Thread-Safe Incident Memory**: Dynamically reads and writes to `incident_memory.json` with thread locks to store past incident resolutions and execute instantaneous matching fixes.
- **Security Firewall & XSS Protection**: Pre-flight payload scanner blocks adversarial prompt injections, API key headers protect decision endpoints, and HTML escaping prevents dashboard Stored XSS.
- **Cloud Run Ready**: Containerized deployment pipeline supporting configurable GCP projects and regions (`deploy.sh`).

---

## Prerequisites

- **Python**: `>=3.11, <3.14`
- **uv**: Dependency manager ([Installation Guide](https://docs.astral.sh/uv/getting-started/installation/))

---

## Local Development Setup

1. **Navigate to the Project Directory:**
   ```bash
   cd netsentinel-coordinator
   ```

2. **Install Dependencies:**
   ```bash
   uv sync
   ```

3. **Set Environment Variables:**
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   
   # Optional: Require API Key for approval decision API endpoints
   export APPROVAL_API_KEY="your-secret-approval-key"
   
   # Optional: Configure allowed CORS origins
   export ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"
   ```

4. **Run the FastAPI Server Locally:**
   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```

5. **Open the Operator & Audit Console:**
   * **Dashboard UI**: Navigate to [http://localhost:8000/dashboard](http://localhost:8000/dashboard) to view pending actions, audit logs, set API keys, and approve/deny SRE operations.
   * **Interactive Swagger Docs**: Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) to test API endpoints interactively.

---

## Triggering an SRE Webhook Alert

Send a mock webhook alert payload to the alert gateway using `curl`:

```bash
curl -X POST http://localhost:8000/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "INC-9999",
    "source": "Prometheus",
    "severity": "CRITICAL",
    "title": "CPU Overutilization",
    "target_resource": "payment-api-deployment",
    "namespace": "default",
    "description": "Payment API CPU usage exceeded threshold limit of 90%"
  }'
```

* **Observe the Workflow**:
  1. The API terminal generates a pending approval request.
  2. Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard).
  3. Notice the 60-second live expiry timer and high-risk modal confirmation.
  4. Click **Approve** or **Deny** to resume backend execution.
  5. Switch to the **Audit History** tab to inspect the logged decision record.

---

## Testing & Quality Assurance

### Run Unit Tests
```bash
uv run pytest tests/unit
```

### Run Integration Tests
```bash
uv run pytest tests/integration
```

### ADK Agent Evaluation Suite
```bash
agents-cli eval generate
agents-cli eval grade
```

### Linter & Type Checker
```bash
# Run Ruff linter
uv run ruff check .

# Run Ty type checker
uv run ty
```

---

## Environment Variables

| Variable | Required | Description | Default |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Yes** | Gemini API Key for Google ADK LLM calls | — |
| `APPROVAL_API_KEY` | Optional | Secret key required in `X-API-Key` header for decisions | Unset (Open for local dev) |
| `ALLOWED_ORIGINS` | Optional | Comma-separated CORS allowed origins | `http://localhost:8000,http://127.0.0.1:8000` |
| `GCP_PROJECT_ID` | Optional | Target GCP project ID for `deploy.sh` | Default project in `deploy.sh` |
| `GCP_REGION` | Optional | Target GCP region for Cloud Run deployment | `us-central1` |
| `INTEGRATION_TEST_MOCK_APPROVAL` | Optional | Set to `TRUE` to bypass manual polling during automated integration tests | `FALSE` |

---

## Cloud Deployment

This repository includes a `Dockerfile` and automated deployment script for **Google Cloud Run**.

1. **Authenticate Google Cloud CLI (`gcloud`):**
   ```bash
   gcloud auth login
   ```

2. **Run Deployment Pipeline:**
   ```bash
   export GCP_PROJECT_ID="your-gcp-project-id"
   export GCP_REGION="us-central1"
   export GEMINI_API_KEY="your-gemini-api-key"
   
   ./deploy.sh
   ```

The script builds the Docker image via Cloud Build, pushes it to Google Artifact Registry, and deploys the container to Cloud Run.

---

## Architecture & Codebase Structure

```
netsentinel-coordinator/
├── app/
│   ├── agent.py               # ADK agent definitions, tool bindings, and human approval gates
│   ├── approval_endpoints.py  # FastAPI routes for pending approvals, audit history, and decisions
│   ├── approval_store.py      # SQLite database schema and queries for approvals (approvals.db)
│   ├── memory_store.py        # Thread-safe persistent incident memory store (incident_memory.json)
│   └── security_eval.py       # Pre-flight payload security firewall and prompt injection scanner
├── frontend/
│   └── index.html             # Real-time glassmorphic SRE operator console & audit history dashboard
├── tests/
│   ├── unit/                  # Unit test suite for approvals, security firewall, and memory store
│   ├── integration/           # Integration & server E2E test flows
│   └── eval/                  # ADK agent evaluation datasets and metrics configuration
├── infra_mcp_server.py        # FastMCP server serving Kubernetes log and network latency tools
├── main.py                    # FastAPI application entrypoint and middleware configuration
├── deploy.sh                  # Automated Cloud Build and Cloud Run deployment pipeline
├── service.yaml               # Knative service specification for Cloud Run
├── agents-cli-manifest.yaml   # ADK framework deployment manifest
├── GEMINI.md                  # ADK agent system guidance
└── pyproject.toml             # Project metadata, dependencies, ruff, ty, and pytest configuration
```
