Use this skill when developing privacy, safety, and human-review controls for the Newcomer webapp.

Trigger this skill for requests involving PII redaction, prompt-injection detection, uploaded forms, pasted eligibility descriptions, secure logging, security-review routing, human caseworker/admin review, compliance notes, or any change that could allow raw sensitive user content to reach an LLM node, recommendation step, document-analysis step, benefits-matching step, logs, or human-review payload.

The security checkpoint protects newcomer identity data while still allowing the agent to use non-sensitive context such as origin, destination, age, household size, and high-level needs. Suspicious prompt-injection or policy-bypass content should route to human review instead of continuing through automated LLM analysis.

When using this skill:

1. Keep `security_checkpoint` as the first graph node after `START`.
2. Redact sensitive values and track only redaction categories, never raw values.
3. Detect instruction override, forced approval, hidden-policy exfiltration, eligibility fabrication, and safety-bypass attempts before LLM processing.
4. Ensure `RequestInput` follow-ups and clarification responses are screened before they re-enter the graph.
5. Add or update tests for every new redaction category, injection indicator, or route.

Load `references/security-rules.md` when changing security screening code, log payloads, review payloads, prompt-injection patterns, or compliance-review behavior.
Use this skill when developing privacy, safety, and human-review controls for the Newcomer webapp.

Trigger this skill for requests involving PII redaction, prompt-injection detection, uploaded forms, pasted eligibility descriptions, secure logging, security-review routing, human caseworker/admin review, compliance notes, or any change that could allow raw sensitive user content to reach an LLM node, recommendation step, document-analysis step, benefits-matching step, logs, or human-review payload.

The security checkpoint protects newcomer identity data while still allowing the agent to use non-sensitive context such as origin, destination, age, household size, and high-level needs. Suspicious prompt-injection or policy-bypass content should route to human review instead of continuing through automated LLM analysis.

When using this skill:

1. Keep `security_checkpoint` as the first graph node after `START`.
2. Redact sensitive values and track only redaction categories, never raw values.
3. Detect instruction override, forced approval, hidden-policy exfiltration, eligibility fabrication, and safety-bypass attempts before LLM processing.
4. Ensure `RequestInput` follow-ups and clarification responses are screened before they re-enter the graph.
5. Add or update tests for every new redaction category, injection indicator, or route.

Load `references/security-rules.md` when changing security screening code, log payloads, review payloads, prompt-injection patterns, or compliance-review behavior.
