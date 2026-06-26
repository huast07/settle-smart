---
name: customization-skill
description: Decide which essential goods and services matter most for a newcomer household before searching for loyalty, rewards, discount, and member programs.
---

# Customization Skill

Use this skill when the workflow has a structured newcomer profile and needs to choose essential categories before local program search.

## Workflow

1. Read the user profile, including destination, age, family size, household member ages, and constraints or preferences.
2. Read the origin-to-destination comparison. Use it as context, not as a substitute for the user's stated needs.
3. Select essential categories that deserve loyalty or reward program search. Start with food, transit, banking, healthcare/pharmacy, housing/utilities, cellular/telecommunications, and credit-building when age-eligible.
4. For healthcare/pharmacy, consider both commercial pharmacy loyalty or prescription-savings programs and official government healthcare, coverage, or prescription benefit programs. Do not infer medical eligibility beyond official criteria.
5. Add demographic categories only when supported by the profile, such as family and child essentials, senior discounts, student/youth programs, accessibility needs, or bulk purchasing.
6. Assign each category a priority of `high`, `medium`, or `low`. Prefer fewer high priorities so search can stay focused.
7. For each category, provide a practical rationale and 2-4 search focuses that can be turned into local search queries.

For detailed category heuristics, load `references/essential-categories.md` only if the profile includes children, older adults, students/youth, disability/accessibility needs, large households, or unclear household composition.

## Output Rules

- Return categories that are actionable for local loyalty, rewards, discount, member, or essential-service programs.
- Do not include luxury, entertainment-only, or travel categories unless the user explicitly asks.
- Do not provide legal, medical, or financial advice.
- Preserve uncertainty in the rationale when a profile field is missing or ambiguous.
