# NetSentinel AI

NetSentinel AI is a production-grade, multi-agent AI infrastructure remediator built using the Google Agent Development Kit (ADK) and FastAPI. It operates as an autonomous Site Reliability Engineer (SRE) to catch webhook alerts from monitoring tools (like Datadog or Prometheus), query system logs, and automatically generate infrastructure remediation plans.

## Features
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

2. **Set your Gemini API Key:**
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

3. **Run the FastAPI Server Locally:**
   ```bash
   uv run uvicorn main:app --reload --port 8000
   ```
   *Navigate to [http://localhost:8000/docs](http://localhost:8000/docs) to access the interactive Swagger UI and test the API directly from your browser!*

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
- `app/security_eval.py`: Strict JSON payload sanitation.
- `main.py`: Asynchronous FastAPI entry point.
- `deploy.sh`: Deployment automation pipeline.
- `service.yaml`: Knative configuration specs for Cloud Run.
