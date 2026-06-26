# Settle Smart: Newcomer Rewards Navigator

Settle Smart is an ADK-powered webapp that helps a newcomer or case manager find
local loyalty, rewards, discount, and essential-service programs for a destination
city. The app asks for age, household size, origin location, and destination
location, then uses a graph-based ADK agent to compare the move context, search
for local programs, verify eligibility/signup evidence, and display categorized
recommendations in a friendly dashboard.

The project was built for the Kaggle Vibe Coding Agents capstone. It demonstrates
an ADK workflow, filesystem Agent Skills, tool-based search, security screening,
structured evaluation tests, and a deployable FastAPI frontend.

## What It Recommends

The backend considers essential newcomer categories including:

- Food and groceries
- Transit and mobility
- Banking and credit-building
- Commercial pharmacy programs
- Government healthcare and prescription benefits
- Housing and utilities
- Cellular, telecommunications, and internet access
- Shared household, family, senior, and bulk-purchasing needs when relevant

Recommendations are grouped by category in the UI and include eligibility notes,
signup steps, official links when available, fees/checks, confidence, and caution
notes.

## Architecture

```text
newcomer-agent/
├── app/
│   ├── agent.py                    # ADK Workflow, schemas, security, agent nodes
│   ├── agent_runtime_app.py         # Local/Agent Runtime app wrapper
│   ├── app_utils/                   # Telemetry and feedback helpers
│   └── skills/
│       ├── customization-skill/
│       ├── program-search-skill/
│       ├── eligibility-search-skill/
│       ├── verification-skill/
│       ├── signup-process-skill/
│       └── recommendation-skill/
├── submission_frontend/
│   └── main.py                      # Standalone FastAPI dashboard service
├── tests/                           # Unit, integration, schema, and UI checks
├── Dockerfile                       # Cloud Run container entrypoint
├── CLOUD_RUN_DEPLOY.md              # Cloud Run deployment commands
├── pyproject.toml
└── uv.lock
```

### Request Flow

1. The FastAPI dashboard collects age, household size, origin, and destination.
2. The frontend creates a structured intake prompt and calls the local ADK runtime.
3. `security_checkpoint` redacts sensitive data and detects prompt injection.
4. Profile extraction turns the intake into a typed `NewcomerProfile`.
5. `compare_origin_destination` summarizes practical differences between origin
   and destination.
6. `customize_essentials` uses the customization skill to choose priority
   essential categories.
7. `build_program_search_prompt` turns those priorities into search objectives
   and official-source verification rules.
8. `discover_local_programs` uses Google Search plus the program, eligibility,
   verification, and signup skills to gather candidate programs.
9. `recommend_programs` uses the recommendation skill to select credible top
   programs per category.
10. The dashboard normalizes the response, groups recommendations by category,
    and displays a slide-out compliance review.

The ADK graph is defined in `app/agent.py` as `root_agent`.

## ADK and Agent Skills

The backend uses ADK 2.x graph workflow primitives:

- `Workflow` and `@node` for explicit orchestration
- `LlmAgent` for profile extraction, comparison, customization, search, and
  recommendation
- `RequestInput` for human-review interrupt paths
- Pydantic schemas for typed handoffs between nodes
- `GoogleSearchTool` for current local program discovery
- `SkillToolset` with local filesystem Agent Skills

Skills keep the model behavior modular:

- `customization-skill`: selects essential categories based on profile and move
  context.
- `program-search-skill`: searches category-by-category and prefers official
  sources.
- `eligibility-search-skill`: captures age, residency, household, credit, fee,
  documentation, and service-area limits.
- `verification-skill`: checks source quality and confidence.
- `signup-process-skill`: identifies practical enrollment paths.
- `recommendation-skill`: ranks verified programs and preserves category labels
  for UI grouping.

## Security Features

The workflow screens user input before model processing. It redacts sensitive
fields such as full names, emails, phone numbers, home addresses, passport
numbers, SIN/SSN-like identifiers, credit card numbers, and bank account details.

Prompt-injection indicators route the request to a human review path instead of
continuing automatically. The final dashboard compliance review also reminds
managers that recommendations are informational and should not be treated as
legal, medical, or financial advice.

## Local Setup

Install dependencies:

```bash
uvx google-agents-cli setup
agents-cli install
```

Create a local environment file at `app/.env`:

```bash
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=<your-gemini-api-key>
```

Do not commit `app/.env`.

## Run Locally

Start the dashboard:

```bash
.venv/bin/python submission_frontend/main.py
```

Open:

```text
http://127.0.0.1:3020
```

Useful endpoints:

```text
GET  /api/health
GET  /api/location-suggestions?q=Brampton
POST /api/recommendations
```

The app uses these environment variables:

- `GOOGLE_API_KEY`: Gemini API key for the backend model.
- `NEWCOMER_AGENT_ROOT`: optional path to the backend root. Defaults to this repo.
- `SUBMISSION_FRONTEND_AGENT_TIMEOUT`: backend timeout in seconds. Defaults to
  `240`.
- `SUBMISSION_FRONTEND_LOCATION_TIMEOUT`: autocomplete geocoder timeout. Defaults
  to `1.6`.
- `SUBMISSION_FRONTEND_USE_VERTEX_RUNTIME`: set to `1` to avoid the local
  integration-test runtime mode.

## Tests

Run the full suite:

```bash
.venv/bin/python -m pytest tests -q
```

Current coverage includes:

- Security redaction and prompt-injection detection
- Skill loading
- Category selection for household, telecom, pharmacy, and healthcare benefits
- Schema tolerance for model output variations
- Timeout handling
- Location autocomplete behavior
- Dashboard response shaping
- Inline JavaScript syntax checks for the frontend

## Cloud Run Deployment

The repo includes a `Dockerfile` for Cloud Run. The container runs:

```bash
python -m uvicorn submission_frontend.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

For the full deployment path, see `CLOUD_RUN_DEPLOY.md`.

At a high level:

1. Push this repo to GitHub.
2. In Cloud Run, choose GitHub continuous deployment with Cloud Build.
3. Use `Dockerfile` as the build type.
4. Set container port to `8080`.
5. Store `GOOGLE_API_KEY` in Secret Manager, not in GitHub.
6. Add:

```text
NEWCOMER_AGENT_ROOT=/app
SUBMISSION_FRONTEND_AGENT_TIMEOUT=540
```

For demos, consider:

```text
memory: 2Gi or 4Gi
cpu: 1
concurrency: 1
timeout: 600
max instances: 1
```

## Notes for Submission

This project intentionally avoids hardcoded recommendation results. The frontend
does not make approval/rejection decisions; it displays agent-produced
recommendations and a compliance review. Location autocomplete uses broad
geocoder-backed suggestions plus a typed-location fallback, so users can enter
any origin or destination location.

