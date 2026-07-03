# NetSentinel AI

NetSentinel AI is a production-grade, multi-agent AI infrastructure remediator built using the Google Agent Development Kit (ADK) and FastAPI. It operates as an autonomous Site Reliability Engineer (SRE) to catch webhook alerts from monitoring tools (like Datadog or Prometheus), query system logs, and automatically generate infrastructure remediation plans.

## Features
- **Human-in-the-Loop Approvals**: Holds sensitive agent actions in a pending state, allowing operators to manually inspect and approve/deny actions via a sleek, real-time glassmorphic operator dashboard.
- **Multi-Agent Orchestration**: A lead SRE `Coordinator` routes tasks to specialized sub-agents (e.g., `Log Analyzer`).
- **Persistent Memory**: Dynamically reads and writes to `incident_memory.json` to remember past incidents and execute instantaneous fixes.
- **Security Firewall**: A pre-flight payload scanner intercepts adversarial Prompt Injections before they reach the LLM.
- **FastAPI Webhook Gateway**: Built for cloud-native automated event ingestion.
- **Cloud Run Ready**: Containerized and deployed effortlessly via Google Cloud Run.

---

## Local Development Setup

We use `uv` for lightning-fast dependency management.

1. **Install Dependencies:**
   ```bash
   uv sync
   ```

2. **Run the Unit Tests:**
   Ensure all unit tests are green:
   ```bash
   uv run pytest tests/unit
   ```

3. **Set your Gemini API Key:**
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

4. **Run the FastAPI Server Locally:**
   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```

5. **Open the Operator Console:**
   * **Dashboard UI**: Navigate to [http://localhost:8000/dashboard](http://localhost:8000/dashboard) to view, approve, or deny pending SRE actions.
   * **Swagger API Documentation**: Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) to test the API directly from the interactive docs.

6. **Trigger an Action for Human-in-the-Loop Approval:**
   Send a mock webhook alert payload to the gateway using `curl`:
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
   Observe the API terminal waiting in a pending state, go to the dashboard UI to click **Approve** or **Deny**, and watch the backend resume!

---

## Cloud Deployment

This repository includes a `Dockerfile` and automated deployment script for **Google Cloud Run**.

1. **Ensure you have the Google Cloud CLI (`gcloud`) installed and authenticated:**
   ```bash
   gcloud auth login
   ```

2. **Run the deployment script:**
   *(Ensure your Google Cloud project has an active Billing Account linked)*
   ```bash
   ./deploy.sh
   ```

The script will automatically build your container using Cloud Build, push it to Artifact Registry, and host it live on Cloud Run.

---

## Architecture

- `app/agent.py`: ADK Agent definitions and Human-In-The-Loop configurations.
- `app/approval_store.py`: SQLite database queries and schemas for approvals.
- `app/approval_endpoints.py`: FastAPI endpoints for polling and deciding pending approvals.
- `app/security_eval.py`: Strict JSON payload sanitation.
- `frontend/index.html`: Real-time glassmorphic operator approval dashboard.
- `main.py`: Asynchronous FastAPI entry point.
- `deploy.sh`: Deployment automation pipeline.
- `service.yaml`: Knative configuration specs for Cloud Run.
