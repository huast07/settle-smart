# Newcomer Cloud Run Contract

Load this reference when changing deployment or production-like configuration.

## Runtime Shape

The deployed container runs the FastAPI dashboard:

```bash
python -m uvicorn submission_frontend.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

The dashboard invokes the local ADK backend from the same container using `NEWCOMER_AGENT_ROOT=/app`.

## Required Environment

- `GOOGLE_API_KEY`: Gemini API key, preferably from Secret Manager.
- `NEWCOMER_AGENT_ROOT=/app`: backend root inside the container.
- `SUBMISSION_FRONTEND_AGENT_TIMEOUT`: use a high enough timeout for graph search and model retries, such as `540` for demos.
- `SUBMISSION_FRONTEND_LOCATION_TIMEOUT`: optional geocoder timeout.
- `SUBMISSION_FRONTEND_USE_VERTEX_RUNTIME=1`: optional setting to avoid local integration-test runtime mode.
- `GOOGLE_CLOUD_LOCATION`: only change when needed for model availability.
- `LOGS_BUCKET_NAME`: optional telemetry bucket; do not use it to capture raw prompt content.

## Secret Rules

- Do not commit `app/.env`.
- Do not hardcode API keys, service-account JSON, tokens, or project credentials.
- Use Secret Manager or the deployment platform's secret injection.

## Cloud Run Demo Defaults

Recommended demo settings:

- memory: `2Gi` or `4Gi`
- cpu: `1`
- concurrency: `1`
- timeout: `600`
- max instances: `1`

These defaults reduce concurrent model/search contention during demos.

## Smoke Checks

After deployment:

1. Call `/api/health`.
2. Open the dashboard.
3. Submit a simple profile with age, household size, origin, and destination.
4. Confirm the response includes grouped categories, compliance review, and no request for sensitive identity fields.

## Deployment Safety

Deployment changes must preserve security screening, metadata-only telemetry, and informational-disclaimer behavior.
# Newcomer Cloud Run Contract

Load this reference when changing deployment or production-like configuration.

## Runtime Shape

The deployed container runs the FastAPI dashboard:

```bash
python -m uvicorn submission_frontend.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

The dashboard invokes the local ADK backend from the same container using `NEWCOMER_AGENT_ROOT=/app`.

## Required Environment

- `GOOGLE_API_KEY`: Gemini API key, preferably from Secret Manager.
- `NEWCOMER_AGENT_ROOT=/app`: backend root inside the container.
- `SUBMISSION_FRONTEND_AGENT_TIMEOUT`: use a high enough timeout for graph search and model retries, such as `540` for demos.
- `SUBMISSION_FRONTEND_LOCATION_TIMEOUT`: optional geocoder timeout.
- `SUBMISSION_FRONTEND_USE_VERTEX_RUNTIME=1`: optional setting to avoid local integration-test runtime mode.
- `GOOGLE_CLOUD_LOCATION`: only change when needed for model availability.
- `LOGS_BUCKET_NAME`: optional telemetry bucket; do not use it to capture raw prompt content.

## Secret Rules

- Do not commit `app/.env`.
- Do not hardcode API keys, service-account JSON, tokens, or project credentials.
- Use Secret Manager or the deployment platform's secret injection.

## Cloud Run Demo Defaults

Recommended demo settings:

- memory: `2Gi` or `4Gi`
- cpu: `1`
- concurrency: `1`
- timeout: `600`
- max instances: `1`

These defaults reduce concurrent model/search contention during demos.

## Smoke Checks

After deployment:

1. Call `/api/health`.
2. Open the dashboard.
3. Submit a simple profile with age, household size, origin, and destination.
4. Confirm the response includes grouped categories, compliance review, and no request for sensitive identity fields.

## Deployment Safety

Deployment changes must preserve security screening, metadata-only telemetry, and informational-disclaimer behavior.
