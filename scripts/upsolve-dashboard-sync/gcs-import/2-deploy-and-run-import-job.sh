#!/usr/bin/env bash
# Step 2: Build, push, and run the Cloud Run import job.
#
# Prerequisites:
#   gcloud auth login
#   gcloud config set project aa-cp-npr-01
#   Docker running locally
#
# Usage:
#   ./2-deploy-and-run-import-job.sh
#
# Override any variable by setting it before running:
#   GCS_BLOB=upsolve-sync/my-export.ucf ./2-deploy-and-run-import-job.sh

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GCP_PROJECT="${GCP_PROJECT:-aa-cp-npr-01}"
GCP_REGION="${GCP_REGION:-us-central1}"
ARTIFACT_REGISTRY="${ARTIFACT_REGISTRY:-${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/arthur-docker-hub-enterprise-proxy}"
IMAGE_NAME="upsolve-import-job"
IMAGE_TAG="${IMAGE_TAG:-latest}"
FULL_IMAGE="${ARTIFACT_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

JOB_NAME="${JOB_NAME:-upsolve-import-job}"
GCS_BUCKET="${GCS_BUCKET:-scope-artifacts-dev}"
GCS_BLOB="${GCS_BLOB:-upsolve-sync/dashboard.ucf}"

UPSOLVE_DST_HOST="${UPSOLVE_DST_HOST:-https://upsolve-service-1004733904168.us-central1.run.app}"

# Fetch secrets from GCP Secret Manager (set these as env vars to skip)
UPSOLVE_DST_API_KEY="${UPSOLVE_DST_API_KEY:-$(gcloud secrets versions access latest --secret=arthur_upsolve_api_key --project="${GCP_PROJECT}" 2>/dev/null || echo '')}"
UPSOLVE_DST_CONN_URL="${UPSOLVE_DST_CONN_URL:-$(gcloud secrets versions access latest --secret=upsolve_connection_string --project="${GCP_PROJECT}" 2>/dev/null || echo '')}"

# Optional — only needed if HTTP import fails (blob > 32 MB) and direct DB is used
UPSOLVE_FILES_KEY="${UPSOLVE_FILES_KEY:-}"

# ---------------------------------------------------------------------------
# Build and push
# ---------------------------------------------------------------------------

echo "Building Docker image: ${FULL_IMAGE}"
docker build -t "${FULL_IMAGE}" "$(dirname "$0")/import-job"

echo "Pushing to Artifact Registry..."
docker push "${FULL_IMAGE}"

# ---------------------------------------------------------------------------
# Deploy Cloud Run Job
# ---------------------------------------------------------------------------

echo "Deploying Cloud Run Job: ${JOB_NAME}"

ENV_VARS="GCS_BUCKET=${GCS_BUCKET},GCS_BLOB=${GCS_BLOB},UPSOLVE_DST_HOST=${UPSOLVE_DST_HOST}"

if [[ -n "${UPSOLVE_DST_API_KEY}" ]]; then
  ENV_VARS="${ENV_VARS},UPSOLVE_DST_API_KEY=${UPSOLVE_DST_API_KEY}"
fi
if [[ -n "${UPSOLVE_DST_CONN_URL}" ]]; then
  ENV_VARS="${ENV_VARS},UPSOLVE_DST_CONN_URL=${UPSOLVE_DST_CONN_URL}"
fi
if [[ -n "${UPSOLVE_FILES_KEY}" ]]; then
  ENV_VARS="${ENV_VARS},UPSOLVE_FILES_KEY=${UPSOLVE_FILES_KEY}"
fi

gcloud run jobs deploy "${JOB_NAME}" \
  --image="${FULL_IMAGE}" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT}" \
  --set-env-vars="${ENV_VARS}" \
  --memory=2Gi \
  --task-timeout=600 \
  --max-retries=0

# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

echo "Running job ${JOB_NAME}..."
gcloud run jobs execute "${JOB_NAME}" \
  --region="${GCP_REGION}" \
  --project="${GCP_PROJECT}" \
  --wait

echo ""
echo "Job complete. Check logs with:"
echo "  gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}' \\"
echo "    --project=${GCP_PROJECT} --limit=50 --format='value(textPayload)'"
