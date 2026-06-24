#!/bin/bash

# ==========================================
# NetSentinel AI - Cloud Run Deploy Script
# ==========================================

# 1. Variables
# Replace YOUR_PROJECT_ID with a Google Cloud Project that has an active Billing Account.
# You can create a new project via the Google Cloud Console (https://console.cloud.google.com).
PROJECT_ID="sincere-lexicon-485014-k1" 
REGION="us-central1"
SERVICE_NAME="netsentinel-ai"

# We use Google Artifact Registry to securely store the built container image
IMAGE_TAG="$REGION-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/$SERVICE_NAME:latest"

echo "Deploying NetSentinel AI to Google Cloud Run..."
echo "Project: $PROJECT_ID | Region: $REGION"

# Ensure the application entry point exists
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found! Cannot deploy the FastAPI application."
    exit 1
fi

# Ensure the GEMINI_API_KEY is available in the local environment
if [ -z "$GEMINI_API_KEY" ]; then
    # Fallback to check GOOGLE_API_KEY if they exported that instead
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "ERROR: GEMINI_API_KEY environment variable is not set locally."
        echo "Please run: export GEMINI_API_KEY='your-key' before deploying."
        exit 1
    else
        export GEMINI_API_KEY="$GOOGLE_API_KEY"
    fi
fi

# Set the active gcloud project
gcloud config set project $PROJECT_ID

# NOTE: The APIs must be enabled on your new project for this to work:
# gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# 2. Build the container using Cloud Build and push it to Artifact Registry
echo "Building the Docker image via Cloud Build..."
gcloud builds submit --tag $IMAGE_TAG

# 3. Deploy the container to Cloud Run
# We use the parameters from service.yaml implicitly by deploying the image, 
# dynamically passing the local API key, and allowing unauthenticated access for testing.
echo "Deploying the service to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_TAG \
    --region $REGION \
    --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY,ENVIRONMENT=production" \
    --concurrency 20 \
    --cpu 2 \
    --memory 4Gi \
    --allow-unauthenticated

echo "Deployment complete!"
