# Newcomer ADK Graph Contract

Load this reference when editing the Newcomer webapp graph in `newcomer-agent/app/agent.py`.

## Core Files

- `app/agent.py`: ADK `Workflow`, graph nodes, Pydantic schemas, security controls, LLM nodes, skill toolsets, and final response formatting.
- `app/agent_runtime_app.py`: local and Agent Runtime wrapper.
- `app/skills/`: filesystem ADK runtime skills loaded with `load_skill_from_dir` and exposed through `SkillToolset`.
- `submission_frontend/main.py`: FastAPI dashboard that invokes the backend graph and normalizes artifacts.

## Required Flow

The graph should keep this high-level order:

1. `START -> security_checkpoint`
2. clean payload -> `collect_profile_submission`
3. security event -> `request_security_review`
4. profile extraction -> validation -> optional clarification
5. origin/destination comparison
6. customization context and essentials planning
7. program search prompt
8. local program discovery with search-related skills
9. research packaging
10. recommendation skill
11. final response

## Graph Invariants

- Use ADK 2.x `Workflow`, `@node`, function nodes, explicit edges, and `RequestInput`.
- Do not replace the graph with ADK 1.x `SequentialAgent` or root-level `LlmAgent` orchestration.
- Keep `security_checkpoint` before every LLM, recommendation, benefits-matching, document-analysis, and human-approval step.
- Keep clarification and security-review interrupts resumable with stable interrupt IDs.
- Route prompt-injection cases to `request_security_review`; do not pass suspicious content downstream.
- Preserve `MODEL` unless the user explicitly asks to change it.

## State And Schema Handoffs

Important state keys include:

- `redaction_categories`
- `last_security_checkpoint`
- `security_review_required`
- `newcomer_profile`
- `migration_comparison`
- `customization_context`
- `support_needs_plan`
- `priority_needs_summary`
- `program_search_prompt`
- `program_search_queries`
- `program_research_brief`
- `web_research_summary`

When adding or changing a schema, check all downstream model validators, state consumers, frontend normalization code, and tests.

## Runtime Skill Wiring

The current graph loads runtime skills from `app/skills/`:

- `customization-skill`
- `program-search-skill`
- `eligibility-search-skill`
- `verification-skill`
- `signup-process-skill`
- `recommendation-skill`

Use `SkillToolset` to attach skills to the relevant LLM node. Keep search-related skills bundled with `GoogleSearchTool(bypass_multi_tools_limit=True)` for current local discovery.

## Validation Checklist

Run focused tests after graph changes:

- security and helper tests in `tests/unit/test_dummy.py`
- schema tests for search and recommendation outputs
- integration tests for ADK streaming and runtime setup

Use:

```bash
.venv/bin/python -m pytest tests/unit tests/integration -q
```
# Newcomer ADK Graph Contract

Load this reference when editing the Newcomer webapp graph in `newcomer-agent/app/agent.py`.

## Core Files

- `app/agent.py`: ADK `Workflow`, graph nodes, Pydantic schemas, security controls, LLM nodes, skill toolsets, final response formatting.
- `app/agent_runtime_app.py`: local and Agent Runtime wrapper.
- `app/skills/`: filesystem ADK runtime skills loaded with `load_skill_from_dir` and exposed through `SkillToolset`.
- `submission_frontend/main.py`: FastAPI dashboard that invokes the backend graph and normalizes artifacts.

## Required Flow

The graph should keep this high-level order:

1. `START -> security_checkpoint`
2. clean payload -> `collect_profile_submission`
3. security event -> `request_security_review`
4. profile extraction -> validation -> optional clarification
5. origin/destination comparison
6. customization context and essentials planning
7. program search prompt
8. local program discovery with search-related skills
9. research packaging
10. recommendation skill
11. final response

## Graph Invariants

- Use ADK 2.x `Workflow`, `@node`, function nodes, explicit edges, and `RequestInput`.
- Do not replace the graph with ADK 1.x `SequentialAgent` or root-level `LlmAgent` orchestration.
- Keep `security_checkpoint` before every LLM, recommendation, benefits-matching, document-analysis, and human-approval step.
- Keep clarification and security-review interrupts resumable with stable interrupt IDs.
- Route prompt-injection cases to `request_security_review`; do not pass suspicious content downstream.
- Preserve `MODEL` unless the user explicitly asks to change it.

## State And Schema Handoffs

Important state keys include:

- `redaction_categories`
- `last_security_checkpoint`
- `security_review_required`
- `newcomer_profile`
- `migration_comparison`
- `customization_context`
- `support_needs_plan`
- `priority_needs_summary`
- `program_search_prompt`
- `program_search_queries`
- `program_research_brief`
- `web_research_summary`

When adding or changing a schema, check all downstream model validators, state consumers, frontend normalization code, and tests.

## Runtime Skill Wiring

The current graph loads runtime skills from `app/skills/`:

- `customization-skill`
- `program-search-skill`
- `eligibility-search-skill`
- `verification-skill`
- `signup-process-skill`
- `recommendation-skill`

Use `SkillToolset` to attach skills to the relevant LLM node. Keep search-related skills bundled with `GoogleSearchTool(bypass_multi_tools_limit=True)` for current local discovery.

## Validation Checklist

Run focused tests after graph changes:

- security and helper tests in `tests/unit/test_dummy.py`
- schema tests for search and recommendation outputs
- integration tests for ADK streaming and runtime setup

Use:

```bash
.venv/bin/python -m pytest tests/unit tests/integration -q
```
