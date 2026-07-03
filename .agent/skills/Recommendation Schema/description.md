Use this skill when developing recommendation data contracts for the Newcomer webapp.

Trigger this skill for requests that modify `ProgramRecommendation`, `RecommendationPlan`, `DiscoveredProgram`, `ProgramSearchResult`, category labels, confidence values, signup instructions, frontend normalization, markdown fallback parsing, or UI grouping by essential service category.

The recommendation contract connects the ADK graph to the dashboard. Changes must preserve practical, evidence-aware recommendations with provider names, categories, eligibility notes, signup steps, official URLs, costs or fees, confidence, and caution notes.

When using this skill:

1. Update backend Pydantic schemas and frontend normalization together.
2. Preserve category labels so the dashboard can group food, transit, banking, healthcare/pharmacy, housing/utilities, telecom, household, senior, family, and credit-building recommendations.
3. Keep confidence values constrained to `high`, `medium`, or `low`.
4. Do not allow invented URLs, rewards, fees, eligibility, or signup steps.
5. Update schema and parser tests when field names, defaults, coercion, or markdown formatting changes.

Load `references/recommendation-contract.md` when changing recommendation schemas, output formatting, frontend normalization, category taxonomy, or ranking behavior.
Use this skill when developing recommendation data contracts for the Newcomer webapp.

Trigger this skill for requests that modify `ProgramRecommendation`, `RecommendationPlan`, `DiscoveredProgram`, `ProgramSearchResult`, category labels, confidence values, signup instructions, frontend normalization, markdown fallback parsing, or UI grouping by essential service category.

The recommendation contract connects the ADK graph to the dashboard. Changes must preserve practical, evidence-aware recommendations with provider names, categories, eligibility notes, signup steps, official URLs, costs or fees, confidence, and caution notes.

When using this skill:

1. Update backend Pydantic schemas and frontend normalization together.
2. Preserve category labels so the dashboard can group food, transit, banking, healthcare/pharmacy, housing/utilities, telecom, household, senior, family, and credit-building recommendations.
3. Keep confidence values constrained to `high`, `medium`, or `low`.
4. Do not allow invented URLs, rewards, fees, eligibility, or signup steps.
5. Update schema and parser tests when field names, defaults, coercion, or markdown formatting changes.

Load `references/recommendation-contract.md` when changing recommendation schemas, output formatting, frontend parsers, category taxonomy, or ranking behavior.
