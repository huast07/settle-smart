---
name: signup-process-skill
description: Determine practical enrollment paths, signup steps, app or account requirements, fees, and verification tasks for loyalty and rewards programs.
---

# Signup Process Skill

Use this skill after candidate programs and eligibility notes are identified.

## Workflow

1. Locate the official signup path for each program when available.
2. Determine whether signup happens online, in an app, in person, by card/account enrollment, through a transit/provider account, or through a carrier/internet-provider account.
3. Capture basic steps a manager can review before helping a newcomer enroll.
4. Flag fees, credit checks, required accounts, mobile app requirements, identity checks, or documentation language when sources mention them.
5. For government healthcare or prescription benefits, describe only the official application or verification path and avoid advising on medical care or eligibility beyond source evidence.
6. If signup steps are unclear, provide a conservative verification step instead of inventing details.

## Output Rules

- Every discovered program should have `signup_path` or a concise note explaining how to verify signup.
- Recommendation-ready programs should be easy to explain in 1-3 signup steps.
- Use official signup pages or provider help pages for steps whenever possible.
- Do not ask for passport numbers, immigration IDs, bank account details, or home addresses in this workflow.
