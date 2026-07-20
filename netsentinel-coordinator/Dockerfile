# Stage 1: Build & Environment Setup
FROM python:3.12-slim

# Install uv by copying the compiled binaries from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Enable bytecode compilation to improve startup time
ENV UV_COMPILE_BYTECODE=1

# Copy dependency definition first to leverage Docker layer caching
COPY pyproject.toml ./

# Sync the dependencies to create the virtual environment inside the container
# If you eventually add a uv.lock file, change this to: uv sync --frozen
RUN uv sync

# Copy application code
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY infra_mcp_server.py .
COPY core_test.py .
COPY main.py .
COPY incident_memory.json .

# Expose port 8080 (default for Cloud Run, useful if you add a FastAPI/Flask server later)
EXPOSE 8080

# Run the FastAPI web server
CMD ["sh", "-c", "echo $GCP_CREDENTIALS_JSON > /tmp/gcp-credentials.json && uv run uvicorn main:app --host 0.0.0.0 --port 8080"]