# Newcomer Evaluation Playbook

Load this reference when adding tests, eval datasets, or regression checks.

## Deterministic Test Surface

Use unit tests for:

- profile completeness and missing-field detection
- demographic category selection
- Pydantic schema coercion and defaults
- PII redaction and prompt-injection indicators
- runtime skill loading and reference availability
- frontend parser and response-shaping helpers
- timeout and location-suggestion behavior

Use integration tests for:

- ADK `root_agent` streaming
- local in-memory Agent Runtime setup under `INTEGRATION_TEST=TRUE`
- feedback registration
- FastAPI endpoints
- dashboard backend error handling

## Eval Scenario Coverage

Eval datasets should include:

- single adult, family household, large household, senior, and student/youth profiles
- destinations with city, region, province/state, and country specificity
- missing fields that should trigger clarification
- local program categories: grocery, transit, banking, credit cards, healthcare/pharmacy, housing/utilities, telecom/internet, family, bulk household, senior
- adversarial payloads with prompt injection and sensitive identifiers
- weak-evidence cases where the right answer is fewer recommendations with caveats

## Recommendation Quality Checks

A good result should:

- use the origin/destination comparison as context
- prioritize essentials based on age and household size
- recommend named local programs, not generic categories
- include official URLs when evidence supports them
- state eligibility limits, fees, credit checks, service-area limits, and signup steps
- distinguish public benefits from commercial rewards programs
- avoid legal, medical, and financial advice

## Commands

Run targeted tests first. For broader checks from the `newcomer-agent` root:

```bash
.venv/bin/python -m pytest tests -q
```

Use `agents-cli eval` only when credentials and model access are configured. Keep eval artifacts out of source control unless the project intentionally tracks them.

## Regression Notes

Do not make live web availability a brittle unit-test expectation. Prefer schema, routing, and evidence-contract assertions. Use evals or mocked search evidence for quality comparisons.
# Newcomer Evaluation Playbook

Load this reference when adding tests, eval datasets, or regression checks.

## Deterministic Test Surface

Use unit tests for:

- profile completeness and missing-field detection
- demographic category selection
- Pydantic schema coercion and defaults
- PII redaction and prompt-injection indicators
- runtime skill loading and reference availability
- frontend parser and response-shaping helpers
- timeout and location-suggestion behavior

Use integration tests for:

- ADK `root_agent` streaming
- local in-memory Agent Runtime setup under `INTEGRATION_TEST=TRUE`
- feedback registration
- FastAPI endpoints
- dashboard backend error handling

## Eval Scenario Coverage

Eval datasets should include:

- single adult, family household, large household, senior, and student/youth profiles
- destinations with city, region, province/state, and country specificity
- missing fields that should trigger clarification
- local program categories: grocery, transit, banking, credit cards, healthcare/pharmacy, housing/utilities, telecom/internet, family, bulk household, senior
- adversarial payloads with prompt injection and sensitive identifiers
- weak-evidence cases where the right answer is fewer recommendations with caveats

## Recommendation Quality Checks

A good result should:

- use the origin/destination comparison as context
- prioritize essentials based on age and household size
- recommend named local programs, not generic categories
- include official URLs when evidence supports them
- state eligibility limits, fees, credit checks, service-area limits, and signup steps
- distinguish public benefits from commercial rewards programs
- avoid legal, medical, and financial advice

## Commands

Run targeted tests first. For broader checks from the `newcomer-agent` root:

```bash
.venv/bin/python -m pytest tests -q
```

Use `agents-cli eval` only when credentials and model access are configured. Keep eval artifacts out of source control unless the project intentionally tracks them.

## Regression Notes

Do not make live web availability a brittle unit-test expectation. Prefer schema, routing, and evidence-contract assertions. Use evals or mocked search evidence for quality comparisons.
