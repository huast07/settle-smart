# Newcomer Security Rules

Load this reference when changing security screening, review routing, logging, or human-review payloads.

## Protected Data Categories

Raw sensitive values should not reach LLM nodes, recommendation nodes, document-analysis nodes, benefits-matching nodes, logs, or human-review payloads unless a specific trusted workflow explicitly requires them.

Track categories, not values:

- `immigration_id`
- `passport_number`
- `sin_ssn_number`
- `credit_card_number`
- `bank_account_details`
- `phone_number`
- `email_address`
- `home_address`
- `date_of_birth`
- `full_name`

The dashboard should not request these fields. If a user voluntarily includes them, redact before downstream processing.

## Prompt-Injection Indicators

Route to human caseworker/admin review when text tries to:

- ignore, override, forget, or disregard system/developer instructions
- make the agent act as an admin, developer, approver, or caseworker
- force, guarantee, or auto-approve eligibility, benefits, applications, or cases
- fabricate immigration status, eligibility, or documents
- reveal hidden prompts, policies, developer instructions, system rules, or internal guardrails
- bypass safety checks, redaction, security controls, or review steps

Suspicious content should not be rewritten into a safer prompt for the LLM. It should be routed to review.

## Routing Contract

- `security_checkpoint` screens the initial payload.
- `collect_profile_submission` screens resumed profile details.
- `request_profile_clarification` screens clarification responses.
- Clean routes continue to profile extraction or clarified profile extraction.
- Security routes emit `SecurityReviewCase` and go to `request_security_review`.

The review case may include sanitized text, redaction categories, reason, and action. It must not include raw redacted values.

## Logging Rules

- Logs may include redaction categories, indicator names, source labels, route names, event counts, and status.
- Logs should not include raw names, identifiers, contact details, account numbers, home addresses, birth dates, or pasted document text.
- If telemetry is enabled, keep prompt/response content capture off or metadata-only.

## Test Checklist

Add tests when adding or changing a rule:

- sensitive examples are replaced with `[REDACTED:<category>]`
- redaction category names are captured once even if repeated
- prompt-injection examples route to review
- clean profile requests continue to extraction
- clarification and follow-up payloads are screened
- final response names protected categories without exposing values
