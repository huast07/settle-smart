# Newcomer FastAPI Frontend Contract

Load this reference when changing `newcomer-agent/submission_frontend/main.py`.

## API Endpoints

- `GET /`: returns the dashboard HTML.
- `GET /api/health`: reports whether the backend root exists.
- `GET /api/location-suggestions?q=...`: returns geocoder-backed suggestions plus a typed fallback.
- `POST /api/recommendations`: accepts newcomer intake and returns dashboard-ready recommendations.

## Intake Contract

`NewcomerIntake` collects:

- `age`
- `family_size`
- `origin_location`
- `destination_location`

The frontend intentionally avoids collecting home address, full legal name, passport number, immigration ID, SIN/SSN, phone, email, bank account, or credit-card details.

## Backend Prompt Contract

`_build_agent_prompt` should:

- preserve user-provided location specificity
- mention origin and destination as locations, not necessarily countries
- include age and household size
- avoid asking for a home address
- ask for local loyalty, rewards, discounts, member programs, banking, transit, grocery, pharmacy, healthcare benefits, housing/utilities, telecom/internet, and newcomer-friendly essentials
- request official URLs, signup steps, fees/checks, eligibility caveats, confidence, and compliance review

## Response Contract

The dashboard expects:

- `profile`
- `agent_mode`
- `opening_summary`
- `comparison_context`
- `destination_theme`
- `destination_summary`
- `priority_categories`
- `categories`
- `next_steps`
- `welcome`
- `compliance_review`
- `raw_agent_text`
- `latency_ms`

Each normalized recommendation should include:

- `program_name`
- `provider`
- `category`
- `why_recommended`
- `eligibility_notes`
- `signup_instructions`
- `official_url`
- `cost_or_fees`
- `confidence`
- `caution_notes`

## Error Behavior

- Return `504 backend_agent_timeout` when the ADK backend exceeds `SUBMISSION_FRONTEND_AGENT_TIMEOUT`.
- Return `502 backend_agent_unavailable` for credentials, model, search, or runtime failures.
- Keep suggested fixes actionable for local demos.

## Test Checklist

Update tests when changing intake fields, response fields, markdown parsing, timeout behavior, location suggestions, or compliance review fields.
# Newcomer FastAPI Frontend Contract

Load this reference when changing `newcomer-agent/submission_frontend/main.py`.

## API Endpoints

- `GET /`: returns the dashboard HTML.
- `GET /api/health`: reports whether the backend root exists.
- `GET /api/location-suggestions?q=...`: returns geocoder-backed suggestions plus a typed fallback.
- `POST /api/recommendations`: accepts newcomer intake and returns dashboard-ready recommendations.

## Intake Contract

`NewcomerIntake` collects:

- `age`
- `family_size`
- `origin_location`
- `destination_location`

The frontend intentionally avoids collecting home address, full legal name, passport number, immigration ID, SIN/SSN, phone, email, bank account, or credit-card details.

## Backend Prompt Contract

`_build_agent_prompt` should:

- preserve user-provided location specificity
- mention origin and destination as locations, not necessarily countries
- include age and household size
- avoid asking for a home address
- ask for local loyalty, rewards, discounts, member programs, banking, transit, grocery, pharmacy, healthcare benefits, housing/utilities, telecom/internet, and newcomer-friendly essentials
- request official URLs, signup steps, fees/checks, eligibility caveats, confidence, and compliance review

## Response Contract

The dashboard expects:

- `profile`
- `agent_mode`
- `opening_summary`
- `comparison_context`
- `destination_theme`
- `destination_summary`
- `priority_categories`
- `categories`
- `next_steps`
- `welcome`
- `compliance_review`
- `raw_agent_text`
- `latency_ms`

Each normalized recommendation should include:

- `program_name`
- `provider`
- `category`
- `why_recommended`
- `eligibility_notes`
- `signup_instructions`
- `official_url`
- `cost_or_fees`
- `confidence`
- `caution_notes`

## Error Behavior

- Return `504 backend_agent_timeout` when the ADK backend exceeds `SUBMISSION_FRONTEND_AGENT_TIMEOUT`.
- Return `502 backend_agent_unavailable` for credentials, model, search, or runtime failures.
- Keep suggested fixes actionable for local demos.

## Test Checklist

Update tests when changing intake fields, response fields, markdown parsing, timeout behavior, location suggestions, or compliance review fields.
