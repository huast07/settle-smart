Use this skill when developing the Newcomer webapp's FastAPI dashboard integration in `newcomer-agent/submission_frontend/main.py`.

Trigger this skill for requests involving `/api/recommendations`, `/api/location-suggestions`, `/api/health`, dashboard response shaping, backend-agent invocation, timeout handling, location autocomplete, frontend grouping of recommendation categories, compliance review display, raw ADK event parsing, or changes to the intake fields collected by the UI.

The frontend should collect only the profile fields needed for the agent: origin location, destination location, age, and household size. It should not ask for passport numbers, immigration IDs, phone numbers, emails, bank details, credit-card numbers, home addresses, or full legal names.

When using this skill:

1. Keep the API contract aligned with `NewcomerIntake`, `RecommendationPlan`, and the normalized dashboard response.
2. Preserve fallback parsing for markdown output when structured agent artifacts are unavailable.
3. Keep user-facing errors practical for local demos: distinguish timeouts from credential, model, search, or backend availability failures.
4. Ensure compliance review messaging continues to flag verification, fees, eligibility limits, and no legal, medical, or financial advice.
5. Update endpoint and frontend-shaping tests when response fields or parsing rules change.

Load `references/frontend-contract.md` when changing dashboard API schemas, response normalization, timeout behavior, location suggestions, or compliance UI data.
Use this skill when developing the Newcomer webapp's FastAPI dashboard integration in `newcomer-agent/submission_frontend/main.py`.

Trigger this skill for requests involving `/api/recommendations`, `/api/location-suggestions`, `/api/health`, dashboard response shaping, backend-agent invocation, timeout handling, location autocomplete, frontend grouping of recommendation categories, compliance review display, raw ADK event parsing, or changes to the intake fields collected by the UI.

The frontend should collect only the profile fields needed for the agent: origin location, destination location, age, and household size. It should not ask for passport numbers, immigration IDs, phone numbers, emails, bank details, credit-card numbers, home addresses, or full legal names.

When using this skill:

1. Keep the API contract aligned with `NewcomerIntake`, `RecommendationPlan`, and the normalized dashboard response.
2. Preserve fallback parsing for markdown output when structured agent artifacts are unavailable.
3. Keep user-facing errors practical for local demos: distinguish timeouts from credential, model, search, or backend availability failures.
4. Ensure compliance review messaging continues to flag verification, fees, eligibility limits, and no legal, medical, or financial advice.
5. Update endpoint and frontend-shaping tests when response fields or parsing rules change.

Load `references/frontend-contract.md` when changing dashboard API schemas, response normalization, timeout behavior, location suggestions, or compliance UI data.
