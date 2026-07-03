Use this skill when developing logging, telemetry, feedback, and operational visibility for the Newcomer webapp.

Trigger this skill for requests involving Agent Runtime setup, Google Cloud Logging, OpenTelemetry, GenAI telemetry, feedback capture, event counts, compliance review data, debug traces, local integration-test runtime behavior, or any logging change that might expose sensitive newcomer data.

Observability should help developers debug graph execution, deployment issues, timeouts, user feedback, and recommendation quality without logging raw PII, raw prompt content, hidden policies, or unredacted uploaded text.

When using this skill:

1. Keep prompt-response content capture disabled or set to metadata-only mode.
2. Log feedback and operational metadata through structured fields, not raw sensitive payloads.
3. Preserve local in-memory services for `INTEGRATION_TEST=TRUE` so tests do not require live Agent Runtime or GCP credentials.
4. Keep dashboard compliance review data aligned with security redactions, event counts, interruption messages, and backend error details.
5. Update integration tests when runtime setup, feedback registration, telemetry env vars, or artifact service selection changes.

Load `references/observability-contract.md` when editing `agent_runtime_app.py`, telemetry setup, feedback logging, dashboard compliance data, or production logging behavior.
Use this skill when developing logging, telemetry, feedback, and operational visibility for the Newcomer webapp.

Trigger this skill for requests involving Agent Runtime setup, Google Cloud Logging, OpenTelemetry, GenAI telemetry, feedback capture, event counts, compliance review data, debug traces, local integration-test runtime behavior, or any logging change that might expose sensitive newcomer data.

Observability should help developers debug graph execution, deployment issues, timeouts, user feedback, and recommendation quality without logging raw PII, raw prompt content, hidden policies, or unredacted uploaded text.

When using this skill:

1. Keep prompt-response content capture disabled or set to metadata-only mode.
2. Log feedback and operational metadata through structured fields, not raw sensitive payloads.
3. Preserve local in-memory services for `INTEGRATION_TEST=TRUE` so tests do not require live Agent Runtime or GCP credentials.
4. Keep dashboard compliance review data aligned with security redactions, event counts, interruption messages, and backend error details.
5. Update integration tests when runtime setup, feedback registration, telemetry env vars, or artifact service selection changes.

Load `references/observability-contract.md` when editing `agent_runtime_app.py`, telemetry setup, feedback logging, dashboard compliance data, or production logging behavior.
