Use this skill when developing the Newcomer webapp's ADK 2.x graph workflow in `newcomer-agent/app/agent.py`.

Trigger this skill for requests that add, remove, reorder, or debug graph nodes; edit `Workflow` edges; add `@node` functions; change `LlmAgent` inputs or outputs; add `RequestInput` human-in-the-loop behavior; wire filesystem ADK Skills through `SkillToolset`; or preserve state across profile extraction, security review, local program search, and recommendation steps.

Do not use ADK 1.x orchestration patterns such as `SequentialAgent` as the primary workflow. Keep the explicit graph API: function nodes, typed schemas, edge routes, and `RequestInput` interrupts.

When using this skill:

1. Inspect the current graph before editing. The security checkpoint must stay before every LLM reviewer, benefits-matching, document-analysis, recommendation, or human-approval path.
2. Keep handoffs typed with Pydantic models, and update state keys only when downstream nodes and frontend parsing remain compatible.
3. Preserve model configuration unless the user explicitly asks to change it.
4. Update targeted tests when graph routes, state shape, schemas, or skill toolsets change.
5. Load `references/graph-contract.md` when editing `app/agent.py`, adding graph edges, or debugging missing state between workflow steps.
Use this skill when developing the Newcomer webapp's ADK 2.x graph workflow in `newcomer-agent/app/agent.py`.

Trigger this skill for requests that add, remove, reorder, or debug graph nodes; edit `Workflow` edges; add `@node` functions; change `LlmAgent` inputs or outputs; add `RequestInput` human-in-the-loop behavior; wire filesystem ADK Skills through `SkillToolset`; or preserve state across profile extraction, security review, local program search, and recommendation steps.

Do not use ADK 1.x orchestration patterns such as `SequentialAgent` as the primary workflow. Keep the explicit graph API: function nodes, typed schemas, edge routes, and `RequestInput` interrupts.

When using this skill:

1. Inspect the current graph before editing. The security checkpoint must stay before every LLM reviewer, benefits-matching, document-analysis, recommendation, or human-approval path.
2. Keep handoffs typed with Pydantic models, and update state keys only when downstream nodes and frontend parsing remain compatible.
3. Preserve model configuration unless the user explicitly asks to change it.
4. Update targeted tests when graph routes, state shape, schemas, or skill toolsets change.

Load `references/graph-contract.md` when editing `app/agent.py`, adding graph edges, changing node routes, or debugging missing state between workflow steps.
