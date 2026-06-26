---
name: eligibility-search-skill
description: Identify age, residency, location, household, credit, fee, documentation, and service-area eligibility for discovered newcomer programs.
---

# Eligibility Search Skill

Use this skill after candidate programs have been discovered and before recommending them to a newcomer household.

## Workflow

1. For each candidate program, search or inspect official eligibility language.
2. Capture age requirements, residency or service-area limits, account requirements, student/senior/family conditions, fees, credit checks, and documentation needs.
3. Do not infer immigration status, income, family relationships, or credit eligibility unless the source explicitly says so.
4. If eligibility is unclear, say what must be verified instead of guessing.
5. For household-related programs, use family size as a relevance factor without assuming children unless children are known.

## Output Rules

- Every discovered program should have concise `eligibility_notes`.
- Banking and credit programs must flag fees and credit checks when source evidence mentions them.
- Government healthcare or prescription benefit programs must flag age, residency, immigration-status, income, waiting-period, documentation, and service-area limits when official evidence mentions them.
- Transit, pharmacy, grocery, utility, cellular, and internet programs must flag geographic or service-area limits when relevant.
- Preserve uncertainty rather than turning unclear evidence into confident eligibility.
