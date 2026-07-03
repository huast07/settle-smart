Use this skill when deploying, containerizing, or configuring production-like runtime behavior for the Newcomer webapp.

Trigger this skill for requests involving Cloud Run, Dockerfile changes, environment variables, Secret Manager, Cloud Build, Terraform, service accounts, runtime memory/CPU/timeouts, public dashboard deployment, Agent Runtime setup, rollback, smoke tests, or deployment documentation.

The deployed service runs the FastAPI dashboard and local ADK backend from the same container. It must keep secrets out of the repo, preserve security screening, and avoid prompt-response content logging unless telemetry is explicitly configured in metadata-only mode.

When using this skill:

1. Read `CLOUD_RUN_DEPLOY.md`, `Dockerfile`, and runtime env handling before changing deployment behavior.
2. Keep `GOOGLE_API_KEY` or Vertex credentials in environment or Secret Manager, never in source files.
3. Preserve `NEWCOMER_AGENT_ROOT=/app` and an adequate `SUBMISSION_FRONTEND_AGENT_TIMEOUT` for the multi-step graph workflow.
4. Use Cloud Run settings suited to demos: enough memory, long timeout, low concurrency, and bounded max instances.
5. Add or update smoke checks for `/api/health` and one recommendation request when deployment behavior changes.

Load `references/cloud-run-contract.md` when editing deployment docs, Docker runtime behavior, Terraform, secrets, service config, or production env vars.
Use this skill when deploying, containerizing, or configuring production-like runtime behavior for the Newcomer webapp.

Trigger this skill for requests involving Cloud Run, Dockerfile changes, environment variables, Secret Manager, Cloud Build, Terraform, service accounts, runtime memory/CPU/timeouts, public dashboard deployment, Agent Runtime setup, rollback, smoke tests, or deployment documentation.

The deployed service runs the FastAPI dashboard and local ADK backend from the same container. It must keep secrets out of the repo, preserve security screening, and avoid prompt-response content logging unless telemetry is explicitly configured in metadata-only mode.

When using this skill:

1. Read `CLOUD_RUN_DEPLOY.md`, `Dockerfile`, and runtime env handling before changing deployment behavior.
2. Keep `GOOGLE_API_KEY` or Vertex credentials in environment or Secret Manager, never in source files.
3. Preserve `NEWCOMER_AGENT_ROOT=/app` and an adequate `SUBMISSION_FRONTEND_AGENT_TIMEOUT` for the multi-step graph workflow.
4. Use Cloud Run settings suited to demos: enough memory, long timeout, low concurrency, and bounded max instances.
5. Add or update smoke checks for `/api/health` and one recommendation request when deployment behavior changes.

Load `references/cloud-run-contract.md` when editing deployment docs, Docker runtime behavior, Terraform, secrets, service config, or production env vars.
