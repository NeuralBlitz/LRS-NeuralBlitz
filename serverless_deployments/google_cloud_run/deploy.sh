#!/bin/bash

# NeuralBlitz Google Cloud Run Deployment Script
# Usage: ./deploy.sh [project-id] [region]

set -e

PROJECT_ID=${1:-neuralblitz-project}
REGION=${2:-us-central1}
SERVICE_NAME="neuralblitz-cloud-run"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "========================================="
echo "NeuralBlitz Google Cloud Run Deployment"
echo "========================================="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Image: ${IMAGE_NAME}"
echo ""

# Check prerequisites
echo "Checking prerequisites..."
command -v gcloud >/dev/null 2>&1 || { echo "Google Cloud SDK is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }

# Set GCP project
echo "Setting GCP project..."
gcloud config set project "${PROJECT_ID}"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com \
    storage.googleapis.com \
    pubsub.googleapis.com \
    cloudtrace.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com

# Create service account if it doesn't exist
echo "Creating service account..."
if ! gcloud iam service-accounts describe "${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
    gcloud iam service-accounts create "${SERVICE_NAME}-sa" \
        --display-name="Cloud Run Service Account"
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/datastore.user"
    
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/storage.objectAdmin"
    
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/pubsub.publisher"
    
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/cloudtrace.agent"
    
    echo "Service account created and permissions granted"
else
    echo "Service account already exists"
fi

# Create Pub/Sub topic if it doesn't exist
echo "Creating Pub/Sub topic..."
gcloud pubsub topics describe "neuralblitz-events" 2>/dev/null || \
    gcloud pubsub topics create "neuralblitz-events"

# Create Cloud Storage bucket if it doesn't exist
echo "Creating Cloud Storage bucket..."
if ! gsutil ls -b "gs://${PROJECT_ID}-data" >/dev/null 2>&1; then
    gsutil mb -l "${REGION}" "gs://${PROJECT_ID}-data"
    gsutil versioning set on "gs://${PROJECT_ID}-data"
    echo "Created bucket: gs://${PROJECT_ID}-data"
else
    echo "Bucket gs://${PROJECT_ID}-data already exists"
fi

# Configure Docker authentication
echo "Configuring Docker authentication..."
gcloud auth configure-docker --quiet

# Build and push container image
echo "Building container image..."
docker build -t "${IMAGE_NAME}:latest" .
docker push "${IMAGE_NAME}:latest"

# Alternatively, use Cloud Build
echo "Building with Cloud Build (alternative)..."
# gcloud builds submit --tag "${IMAGE_NAME}:latest"

# Substitute project ID in service.yaml
sed -e "s/PROJECT_ID/${PROJECT_ID}/g" service.yaml > service-deploy.yaml

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}:latest" \
    --platform managed \
    --region "${REGION}" \
    --service-account "${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --allow-unauthenticated \
    --max-instances 100 \
    --min-instances 1 \
    --memory 2Gi \
    --cpu 2 \
    --concurrency 1000 \
    --timeout 300 \
    --set-env-vars "ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},STORAGE_BUCKET=${PROJECT_ID}-data,PUBSUB_TOPIC=neuralblitz-events"

# Get service URL
echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format 'value(status.url)')
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "To test the deployment:"
echo "curl -X POST ${SERVICE_URL}/inference -H 'Content-Type: application/json' -d '{\"input_data\": {\"test\": true}}'"
echo ""
echo "Health check:"
echo "curl ${SERVICE_URL}/health"

# Create Pub/Sub subscription for push notifications
echo ""
echo "Creating Pub/Sub push subscription..."
gcloud pubsub subscriptions describe "neuralblitz-push-sub" 2>/dev/null || \
    gcloud pubsub subscriptions create "neuralblitz-push-sub" \
        --topic="neuralblitz-events" \
        --push-endpoint="${SERVICE_URL}/pubsub" \
        --ack-deadline=60

# Cleanup
rm -f service-deploy.yaml

echo ""
echo "Deployment completed successfully!"
