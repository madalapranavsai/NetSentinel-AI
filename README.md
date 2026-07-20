# NetSentinel AI

[![Tests](https://github.com/madalapranavsai/NetSentinel-AI/actions/workflows/test.yml/badge.svg)](https://github.com/madalapranavsai/NetSentinel-AI/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)
![Status](https://img.shields.io/badge/status-active--development-yellow)

**NetSentinel AI** is a multi-agent infrastructure remediation assistant built on the **Google Agent Development Kit (ADK)** and **FastAPI**. It ingests webhook alerts from monitoring tools, uses a coordinator agent to assess the incident and consult past resolutions, and proposes a remediation plan that a human operator must explicitly approve before anything runs.

This is an actively developed reference implementation — see [Current Limitations](#current-limitations) below for what's stubbed out vs. production-ready before you point it at real infrastructure.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Features](#features)
- [Quickstart](#quickstart)
- [Triggering an Alert](#triggering-an-alert)
- [Testing](#testing)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Current Limitations](#current-limitations)
- [Project Structure](#project-structure)
- [License](#license)

---

## How It Works

```
 Monitoring Tool                FastAPI                 Coordinator Agent
 (Datadog/Prometheus)          /api/v1/alerts             (Gemini, ADK)
        │                          │                            │
        │  POST alert payload      │                            │
        ├─────────────────────────►│                            │
        │                          │  pre-flight security scan  │
        │                          ├───────────────────────────►│
        │                          │                            │  consults incident_memory.json
        │                          │                            │  (past resolutions)
        │                          │                            │
        │                          │                            │  delegates to Log Analyzer
        │                          │                            │  sub-agent (MCP tools)
        │                          │                            │
        │                          │   proposes remediation      │
        │                          │◄───────────────────────────┤
        │                          │                            │
        │                          │  writes to approvals.db,   │
        │                          │  waits for operator         │
        │                          │
        │                          ▼
        │                 Operator Dashboard
        │              (/dashboard — approve / deny)
```

The core design principle: **the agent proposes, a human disposes.** No remediation action executes without an explicit approve/deny from the dashboard or `POST /approvals/{id}/decide`.

---

## Features

- **Human-in-the-Loop Approvals** — sensitive agent actions are held in a pending state until an operator approves or denies them from the dashboard.
- **Audit History** — `GET /approvals/history` returns resolved decisions (`APPROVED`, `DENIED`, `TIMED_OUT`) with timestamp and `decided_by`.
- **High-Risk Confirmation** — `HIGH`/`CRITICAL` risk actions require an extra confirmation step in the dashboard before submission.
- **Multi-Agent Orchestration** — a `Coordinator` agent delegates to specialized sub-agents (e.g. `Log Analyzer`) built on Gemini models via ADK.
- **MCP Tooling** — infrastructure tools (`get_kubernetes_pod_logs`, `check_network_latency`) are exposed to the agent via a FastMCP STDIO server. **Note:** these currently return hardcoded mock data (see [Current Limitations](#current-limitations)) rather than querying live infrastructure.
- **Thread-Safe Incident Memory** — `incident_memory.json` reads/writes are protected by a lock to prevent corruption from concurrent requests within a single process.
- **Pre-Flight Payload Scanner** — a keyword-based filter rejects a known set of prompt-injection phrases before they reach the agent. This is a first line of defense, not a comprehensive guarantee — see [Current Limitations](#current-limitations).
- **Optional API-Key Auth** — setting `APPROVAL_API_KEY` requires an `X-API-Key` header on the decision endpoint.
- **Dashboard XSS-Safe Rendering** — all operator-facing dynamic content is HTML-escaped before insertion into the DOM.
- **Cloud Run Ready** — containerized with a scripted Cloud Build → Artifact Registry → Cloud Run deployment pipeline.

---

## Quickstart

1. **Navigate to the project directory:**
   ```bash
   cd netsentinel-coordinator
   ```

2. **Install dependencies** ([uv](https://docs.astral.sh/uv/getting-started/installation/) required; Python `>=3.11, <3.14`):
   ```bash
   uv sync
   ```

3. **Set environment variables:**
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"

   # Strongly recommended even for local dev — see Current Limitations
   export APPROVAL_API_KEY="your-secret-approval-key"

   export ALLOWED_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"
   ```

4. **Run the server:**
   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```

5. **Open the console:**
   - Dashboard: [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
   - Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Triggering an Alert

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

Then:
1. Open the [dashboard](http://localhost:8000/dashboard) and watch the pending approval appear (60-second expiry timer).
2. **Approve** or **Deny** the action — high-risk items require a confirmation modal.
3. Check the **Audit History** tab to see the logged decision.

---

## Testing

```bash
# Unit tests
uv run pytest tests/unit

# Integration tests
uv run pytest tests/integration

# With coverage
uv run pytest --cov=app --cov-report=term-missing tests/unit
```

CI runs the unit test suite on every push and pull request via [GitHub Actions](.github/workflows/test.yml).

```bash
# Linting and type checking
uv run ruff check .
uv run ty

# ADK agent evaluation suite
agents-cli eval generate
agents-cli eval grade
```

---

## Environment Variables

| Variable | Required | Description | Default |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Yes** | Gemini API key for ADK LLM calls | — |
| `APPROVAL_API_KEY` | Recommended | Secret required in `X-API-Key` header to approve/deny actions. **If unset, the decision endpoint is open to anyone who can reach it.** | Unset |
| `ALLOWED_ORIGINS` | Optional | Comma-separated CORS allow-list | `http://localhost:8000,http://127.0.0.1:8000` |
| `GCP_PROJECT_ID` | Optional | Target GCP project for `deploy.sh` | Default project in script |
| `GCP_REGION` | Optional | Target Cloud Run region | `us-central1` |
| `INTEGRATION_TEST_MOCK_APPROVAL` | Optional | `TRUE` bypasses manual polling in automated tests | `FALSE` |

---

## Deployment

```bash
export GCP_PROJECT_ID="your-gcp-project-id"
export GCP_REGION="us-central1"
export GEMINI_API_KEY="your-gemini-api-key"

./deploy.sh
```

This builds the image via Cloud Build, pushes to Artifact Registry, and deploys to Cloud Run.

> **⚠️ Before deploying anywhere real traffic can reach:**
> `deploy.sh` currently deploys with `--allow-unauthenticated` and does not set `APPROVAL_API_KEY`. As shipped, this means the deployed service — including the approve/deny endpoint — is reachable by anyone with the URL. Set `APPROVAL_API_KEY` as a Cloud Run env var and consider removing `--allow-unauthenticated` (using Cloud Run's IAM-based auth or an API gateway instead) before deploying against real infrastructure.

---

## Current Limitations

Being upfront about what's a solid foundation vs. what's still a stub, so you can decide what needs hardening before relying on this against real infrastructure:

- **MCP infrastructure tools are mocked.** `infra_mcp_server.py` returns hardcoded responses rather than querying real Kubernetes/Prometheus/etc. Wire in real clients before using this for actual remediation.
- **The approval gate is enforced by agent instructions, not code.** The coordinator agent is prompted to always call `request_human_approval` before proposing action — but nothing at the code level prevents a model from skipping it. Treat this as best-effort, not a hard guarantee.
- **The prompt-injection filter is a keyword blocklist.** It catches a fixed set of known phrases and should be treated as a first layer, not a complete defense against adversarial input.
- **Auth is opt-in.** `APPROVAL_API_KEY` gates the decision endpoint only if set, and only that one endpoint — `GET /approvals/pending`, `GET /approvals/history`, and the alert-ingestion webhook are unauthenticated regardless.
- **`decided_by` is self-reported.** The API key (when set) proves the caller had the key, not who the specific operator was — multiple people sharing a key are indistinguishable in the audit log.
- **Incident memory doesn't survive horizontal scaling.** `incident_memory.json` is local to each container instance; if Cloud Run scales beyond one instance, memory won't be shared across them.

---

## Project Structure

```
netsentinel-coordinator/
├── app/
│   ├── agent.py               # ADK agent definitions, tool bindings, approval gates
│   ├── approval_endpoints.py  # Routes for pending approvals, audit history, decisions
│   ├── approval_store.py      # SQLite schema/queries for approvals (approvals.db)
│   ├── memory_store.py        # Thread-safe incident memory (incident_memory.json)
│   └── security_eval.py       # Pre-flight payload scanner / prompt-injection filter
├── frontend/
│   └── index.html             # Operator dashboard (pending + audit history)
├── tests/
│   ├── unit/                  # Approval, security filter, memory store tests
│   ├── integration/           # Integration & server E2E flows
│   └── eval/                  # ADK agent evaluation datasets
├── infra_mcp_server.py        # FastMCP server exposing infra tools (currently mocked)
├── main.py                    # FastAPI entrypoint and middleware
├── deploy.sh                  # Cloud Build + Cloud Run deployment script
├── service.yaml                # Knative service spec
├── GEMINI.md                  # ADK agent system guidance
└── pyproject.toml             # Dependencies, ruff/ty/pytest config
```

---

## License

No license file is currently included in this repository — all rights reserved by default. If you intend for others to use, modify, or contribute to this project, consider adding a `LICENSE` file (e.g. MIT or Apache 2.0).
