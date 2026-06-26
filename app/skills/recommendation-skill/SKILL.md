---
name: recommendation-skill
description: Recommend the best local loyalty and reward programs for a newcomer profile using discovered program evidence and prioritized essentials.
---

# Recommendation Skill

Use this skill when the workflow has a newcomer profile, priority categories, and discovered local program evidence.

## Workflow

1. Load this skill before recommending programs.
2. Match each candidate program against the user's destination, age, household composition, and constraints.
3. Prioritize programs that cover high-priority essentials, have clear signup steps, and are supported by official evidence.
4. Penalize programs with unclear location coverage, high fees, strict credit checks, or weak evidence.
5. For every essential goods or service category, determine the top three loyalty, rewards, member, or discount programs when enough verified evidence exists.
6. If a category has fewer than three credible programs, recommend only the credible programs and preserve the category name.
7. When grocery evidence includes named local chains, recommend the specific chain program rather than a generic grocery category.
8. Explain why each program fits, what eligibility must be checked, and how to sign up.
9. For cellular and telecommunications, consider verified mobile carrier, prepaid plan, internet affordability, multi-line, and bundle reward programs when they serve the user's destination or service area.

For ranking details, load `references/ranking-rubric.md` when more than five candidate programs are available or when two programs serve the same essential category.

## Output Rules

- Do not invent or overstate rewards, eligibility, fees, or signup steps.
- Include official URLs when evidence supports them.
- Preserve category labels so the UI can group recommendations by essential goods or service category.
- Include a basic eligibility summary and signup process for each recommendation.
- Use `high`, `medium`, or `low` confidence for each recommendation.
- For banking and credit cards, mention fees, credit checks, and that this is not financial advice.
- For healthcare/pharmacy, distinguish commercial pharmacy loyalty or prescription savings programs from government healthcare, coverage, or prescription benefits. Do not give medical advice.
- For housing, distinguish rent rewards, utility discounts, tenant benefits, and public assistance.
- For cellular and telecommunications, flag coverage, service-area, contract, device, autopay, credit-check, and household-line requirements when the evidence mentions them.
