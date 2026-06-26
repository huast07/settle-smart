# Cloud Run Deployment

This deploys the public FastAPI dashboard in `submission_frontend/` and runs
the local ADK backend from the same container.

## 1. Set Project Variables

```bash
export PROJECT_ID="<your-google-cloud-project-id>"
export REGION="us-east1"
export SERVICE_NAME="newcomer-rewards-dashboard"

gcloud auth login
gcloud config set project "$PROJECT_ID"
```

## 2. Store Gemini API Key In Secret Manager

Do not commit `app/.env` or pass the API key directly in a deploy command.

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com

gcloud secrets create google-api-key --replication-policy="automatic"
gcloud secrets versions add google-api-key --data-file=-
```

Paste the Gemini API key, then press `Ctrl-D`.

Grant the default Cloud Run runtime service account access to the secret:

```bash
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding google-api-key \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

## 3. Deploy The Dashboard

Run from the repository root:

```bash
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory "2Gi" \
  --cpu "1" \
  --concurrency "1" \
  --timeout "600" \
  --max-instances "1" \
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest" \
  --set-env-vars "NEWCOMER_AGENT_ROOT=/app,SUBMISSION_FRONTEND_AGENT_TIMEOUT=540"
```

The command prints the public service URL when deployment finishes.

## 4. Smoke Test

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"
curl "${SERVICE_URL}/api/health"
open "$SERVICE_URL"
```

## 5. Shut Down After A Demo

```bash
gcloud run services delete "$SERVICE_NAME" --region "$REGION"
```

