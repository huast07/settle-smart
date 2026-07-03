# Newcomer Recommendation Contract

Load this reference when editing recommendation schemas, model output instructions, frontend normalization, or markdown fallback parsing.

## Backend Schemas

Important models in `app/agent.py`:

- `CategoryNeed`: category, priority, rationale, focus.
- `DiscoveredProgram`: program name, provider, category, source URL, evidence summary, eligibility summary, signup path.
- `ProgramSearchResult`: destination, queries used, discovered programs, search summary, source notes.
- `ProgramResearchBrief`: profile, comparison summary, priority summary, categories, queries, search result, web research.
- `ProgramRecommendation`: program name, provider, category, why recommended, eligibility, signup instructions, official URL, fees, confidence, caution notes.
- `RecommendationPlan`: opening summary, comparison context, priority categories, recommendations, next steps, disclaimer.

## Category Taxonomy

Preserve practical essential categories so the UI can group recommendations:

- Food and groceries
- Transit and mobility
- Banking
- Credit cards and credit building
- Healthcare and pharmacy
- Housing and utilities
- Cellular and telecommunications
- Shared household essentials
- Family and child essentials
- Bulk household purchasing
- Senior discounts

New categories are allowed when supported by the profile, but avoid luxury or entertainment-only categories unless explicitly requested.

## Field Rules

- `confidence` should be `high`, `medium`, or `low`.
- `signup_instructions` and list fields should tolerate strings but normalize to lists.
- `official_url` should point to an official source when available.
- `cost_or_fees` should flag fees, credit checks, contracts, or verification needs when evidence mentions them.
- `caution_notes` should carry uncertainty, source weakness, or special eligibility limits.

## Markdown Fallback

`final_response` emits sections that `submission_frontend/main.py` can parse:

- `## Context used`
- `## Priority areas`
- `## Recommended programs`
- `## Next steps`

When changing formatting, update `_parse_markdown_plan` and tests together.

## Ranking Rules

Recommendations should favor:

- destination/service-area fit
- high-priority essential categories
- official source evidence
- clear signup path
- low friction and low fees
- no hard credit check unless clearly caveated

Recommend up to three credible programs per category. Return fewer when evidence is weak instead of filling with invented or low-confidence options.
