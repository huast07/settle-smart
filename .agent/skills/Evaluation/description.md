Use this skill when evaluating or testing the Newcomer webapp and its ADK graph workflow.

Trigger this skill for requests that add pytest coverage, create or revise eval datasets, test profile extraction, validate security screening, check runtime skill loading, verify recommendation schemas, exercise FastAPI endpoints, compare recommendation quality, or debug regressions in local program discovery and dashboard response shaping.

The project needs both deterministic tests and model-facing evals: deterministic tests protect security, schemas, routing, timeout behavior, and frontend normalization; evals check whether the agent produces useful, evidence-aware local program recommendations for varied newcomer profiles.

When using this skill:

1. Prefer fast unit tests for pure Python helpers, schemas, security screening, and frontend normalization.
2. Use integration tests for ADK runtime wiring, streaming behavior, feedback logging, and FastAPI endpoints.
3. Use eval datasets for scenario quality, coverage across destinations, household compositions, missing fields, and adversarial instructions.
4. Avoid asserting hardcoded live program availability unless the test controls the evidence source.
5. Run the narrowest relevant tests first, then broaden before finishing risky changes.

Load `references/evaluation-playbook.md` when writing tests, eval cases, judges, regression scenarios, or verification commands.
Use this skill when evaluating or testing the Newcomer webapp and its ADK graph workflow.

Trigger this skill for requests that add pytest coverage, create or revise eval datasets, test profile extraction, validate security screening, check runtime skill loading, verify recommendation schemas, exercise FastAPI endpoints, compare recommendation quality, or debug regressions in local program discovery and dashboard response shaping.

The project needs both deterministic tests and model-facing evals: deterministic tests protect security, schemas, routing, timeout behavior, and frontend normalization; evals check whether the agent produces useful, evidence-aware local program recommendations for varied newcomer profiles.

When using this skill:

1. Prefer fast unit tests for pure Python helpers, schemas, security screening, and frontend normalization.
2. Use integration tests for ADK runtime wiring, streaming behavior, feedback logging, and FastAPI endpoints.
3. Use eval datasets for scenario quality, coverage across destinations, household compositions, missing fields, and adversarial instructions.
4. Avoid asserting hardcoded live program availability unless the test controls the evidence source.
5. Run the narrowest relevant tests first, then broaden before finishing risky changes.

Load `references/evaluation-playbook.md` when writing tests, eval cases, judges, regression scenarios, or verification commands.
