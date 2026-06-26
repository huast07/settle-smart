---
name: verification-skill
description: Verify source quality, official URLs, current availability, geographic fit, and confidence for discovered loyalty and rewards programs.
---

# Verification Skill

Use this skill when candidate programs need source-quality review before recommendation.

## Workflow

1. Prefer official provider, government health agency, government benefits portal, transit agency, bank, pharmacy, grocery, utility, telecom carrier, internet provider, or retailer pages.
2. Use aggregator, coupon, blog, or forum pages only to discover possible programs, then verify with an official page.
3. Check whether the program serves the user's actual destination or service area.
4. Mark stale, conflicting, undated, third-party-only, or geographically ambiguous evidence as lower confidence.
5. Do not keep candidates that cannot be connected to a real provider, official page, or plausible local service area.

For detailed source-quality rules, load `references/source-quality.md` when sources conflict, evidence is stale, or a program appears only on third-party pages.

## Output Rules

- Every discovered program should have `source_url`, `evidence_summary`, and `confidence`.
- Use `high` when an official source confirms both program and signup path.
- Use `medium` when an official source confirms the program but eligibility or signup details need verification.
- Use `low` when the program likely exists but source quality, location, or current availability is uncertain.
