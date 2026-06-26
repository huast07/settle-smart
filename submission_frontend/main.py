from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field


SERVICE_ROOT = Path(__file__).resolve().parent
DEFAULT_BACKEND_ROOT = SERVICE_ROOT.parent
BACKEND_ROOT = Path(
    os.environ.get("NEWCOMER_AGENT_ROOT", str(DEFAULT_BACKEND_ROOT))
).expanduser().resolve()
DEFAULT_AGENT_TIMEOUT_SECONDS = 240.0
LOCATION_SUGGEST_TIMEOUT_SECONDS = float(
    os.environ.get("SUBMISSION_FRONTEND_LOCATION_TIMEOUT", "1.6")
)

app = FastAPI(
    title="Newcomer Rewards Manager Dashboard",
    description="Standalone dashboard for newcomer loyalty and rewards recommendations.",
    version="0.1.0",
)

_agent_runtime_ready = False
_agent_runtime_lock = asyncio.Lock()


def _format_seconds(value: float) -> str:
    return f"{value:g} second{'s' if value != 1 else ''}"


def _agent_timeout_seconds() -> float:
    raw_value = os.environ.get("SUBMISSION_FRONTEND_AGENT_TIMEOUT")
    if raw_value is None:
        return DEFAULT_AGENT_TIMEOUT_SECONDS

    try:
        timeout = float(raw_value)
    except ValueError as exc:
        raise RuntimeError(
            "SUBMISSION_FRONTEND_AGENT_TIMEOUT must be a positive number of seconds."
        ) from exc

    if timeout <= 0:
        raise RuntimeError(
            "SUBMISSION_FRONTEND_AGENT_TIMEOUT must be greater than zero seconds."
        )
    return timeout


class BackendAgentTimeoutError(TimeoutError):
    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(
            "Backend agent timed out after "
            f"{_format_seconds(timeout_seconds)}. The ADK workflow may still "
            "be waiting on model retries, search grounding, or quota backoff."
        )


class NewcomerIntake(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    age: int = Field(ge=1, le=120)
    family_size: int = Field(default=1, ge=1, le=20)
    origin_location: str = Field(
        min_length=2,
        max_length=220,
        validation_alias=AliasChoices("origin_location", "origin_country"),
    )
    destination_location: str = Field(
        min_length=2,
        max_length=220,
        validation_alias=AliasChoices("destination_location", "destination_country"),
    )


def _clean_location(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _typed_location_suggestion(query: str) -> dict[str, str]:
    cleaned = _clean_location(query)
    return {
        "value": cleaned,
        "label": f"Use “{cleaned}” as typed",
        "source": "typed",
    }


def _dedupe_location_suggestions(
    suggestions: list[dict[str, str]],
    limit: int,
) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for suggestion in suggestions:
        value = str(suggestion.get("value") or "").strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append({**suggestion, "value": value})
        if len(deduped) >= limit:
            break
    return deduped


def _format_nominatim_result(result: dict[str, Any]) -> dict[str, str] | None:
    address = result.get("address") or {}
    primary = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or result.get("name")
    )
    region_parts = [
        address.get("state"),
        address.get("province"),
        address.get("region"),
        address.get("country"),
    ]
    value = ", ".join(part for part in [primary, *region_parts] if part)
    if not value:
        value = str(result.get("display_name") or "").strip()
    if not value:
        return None

    return {
        "value": value,
        "label": str(result.get("display_name") or value),
        "source": "openstreetmap",
    }


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "newcomer-rewards-dashboard/0.1 (local development)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(
        request, timeout=LOCATION_SUGGEST_TIMEOUT_SECONDS
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_nominatim_suggestions(cleaned: str, limit: int) -> list[dict[str, str]]:
    params = urllib.parse.urlencode(
        {
            "q": cleaned,
            "format": "jsonv2",
            "addressdetails": "1",
            "dedupe": "1",
            "limit": str(limit),
            "accept-language": "en",
        }
    )
    payload = _fetch_json(f"https://nominatim.openstreetmap.org/search?{params}")
    results = payload if isinstance(payload, list) else []
    return [
        suggestion
        for item in results
        if isinstance(item, dict)
        for suggestion in [_format_nominatim_result(item)]
        if suggestion
    ][:limit]


def _format_photon_result(feature: dict[str, Any]) -> dict[str, str] | None:
    properties = feature.get("properties") or {}
    primary = (
        properties.get("city")
        or properties.get("name")
        or properties.get("county")
        or properties.get("state")
    )
    region_parts = [
        properties.get("state"),
        properties.get("country"),
    ]
    value = ", ".join(part for part in [primary, *region_parts] if part)
    if not value:
        return None

    return {
        "value": value,
        "label": value,
        "source": "photon",
    }


def _fetch_photon_suggestions(cleaned: str, limit: int) -> list[dict[str, str]]:
    params = urllib.parse.urlencode({"q": cleaned, "limit": str(limit), "lang": "en"})
    payload = _fetch_json(f"https://photon.komoot.io/api/?{params}")
    features = payload.get("features") if isinstance(payload, dict) else []
    feature_list = features if isinstance(features, list) else []
    return [
        suggestion
        for feature in feature_list
        if isinstance(feature, dict)
        for suggestion in [_format_photon_result(feature)]
        if suggestion
    ][:limit]


def _fetch_location_suggestions(query: str, limit: int = 8) -> list[dict[str, str]]:
    cleaned = _clean_location(query)
    if len(cleaned) < 2:
        return []

    suggestions: list[dict[str, str]] = []

    for fetcher in (_fetch_nominatim_suggestions, _fetch_photon_suggestions):
        try:
            suggestions.extend(fetcher(cleaned, limit))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            continue

    suggestions.append(_typed_location_suggestion(cleaned))
    return _dedupe_location_suggestions(suggestions, limit)


def _destination_theme(
    destination: str,
    comparison_context: str,
    priority_categories: list[str],
) -> dict[str, Any]:
    text = f"{destination} {comparison_context} {' '.join(priority_categories)}".lower()
    theme = {
        "name": "warm local welcome",
        "primary": "#0f766e",
        "secondary": "#f59e0b",
        "accent": "#2563eb",
        "soft": "#effaf5",
        "ink": "#17202a",
        "motif": "city lights",
        "description": (
            "A calm city palette based on the agent's destination context and "
            "essential-service priorities."
        ),
    }

    if any(token in text for token in ("san francisco", "bay area", "california", "fog", "transit", "pacific")):
        theme.update(
            {
                "name": "bay breeze",
                "primary": "#0e7490",
                "secondary": "#f97316",
                "accent": "#2563eb",
                "soft": "#e8f7fb",
                "motif": "bay transit lines",
                "description": "Cool bay blues with sunset warmth for a San Francisco landing.",
            }
        )
    elif any(token in text for token in ("toronto", "ontario", "canada", "ttc", "winter")):
        theme.update(
            {
                "name": "bright neighbourhood",
                "primary": "#dc2626",
                "secondary": "#0f766e",
                "accent": "#2563eb",
                "soft": "#fff1f1",
                "motif": "neighbourhood grid",
                "description": "Warm reds and useful greens for a practical Toronto welcome.",
            }
        )
    elif any(token in text for token in ("london", "uk", "united kingdom", "england")):
        theme.update(
            {
                "name": "high street welcome",
                "primary": "#1d4ed8",
                "secondary": "#be123c",
                "accent": "#64748b",
                "soft": "#eef4ff",
                "motif": "high-street routes",
                "description": "Crisp blues and civic reds for navigating local essentials.",
            }
        )
    elif any(token in text for token in ("mumbai", "delhi", "india", "bengaluru")):
        theme.update(
            {
                "name": "market morning",
                "primary": "#c2410c",
                "secondary": "#0f766e",
                "accent": "#a16207",
                "soft": "#fff7ed",
                "motif": "market lanes",
                "description": "Market warmth and practical greens for household essentials.",
            }
        )

    return theme


def _destination_summary(
    origin: str,
    destination: str,
    comparison_context: str,
    priority_categories: list[str],
    family_size: int,
) -> dict[str, Any]:
    categories = [category for category in priority_categories if str(category).strip()]
    category_text = ", ".join(categories[:4])
    if len(categories) > 4:
        category_text = f"{category_text}, and {len(categories) - 4} more"

    context = comparison_context.strip()
    if len(context) > 360:
        context = f"{context[:357].rstrip()}..."

    summary = (
        f"{destination} is being reviewed as the newcomer's destination city, "
        "with recommendations focused on everyday services that make early "
        "settling easier."
    )
    if context:
        summary = (
            f"{summary} The agent used the {origin} to {destination} comparison "
            f"to account for practical differences: {context}"
        )

    return {
        "title": f"Destination snapshot: {destination}",
        "summary": summary,
        "focus": category_text
        or "grocery, transit, banking, pharmacy, housing, telecom, and household essentials",
        "household": (
            f"Household size: {family_size}. The agent prioritizes everyday programs "
            "that can support the whole household."
        ),
    }


def _build_agent_prompt(intake: NewcomerIntake) -> str:
    origin = _clean_location(intake.origin_location)
    destination = _clean_location(intake.destination_location)
    extra_household_members = max(intake.family_size - 1, 0)
    return (
        f"Origin: {origin}. Destination: {destination}. Age: {intake.age}. "
        "Origin and destination are locations as provided by the newcomer. "
        "Use the location specificity given by the newcomer, whether it is a city, "
        "region, province/state, country, or neighborhood. Do not ask for a home address. "
        f"Family or household size: {intake.family_size}. "
        f"Household members and ages: self, age {intake.age}; "
        f"{extra_household_members} additional household member(s), ages not collected. "
        "Use family size as a prioritization factor for essential goods and services "
        "without assuming children unless ages or relationships are provided. "
        "Please recommend local loyalty, rewards, discount, member, banking, transit, "
        "grocery, commercial pharmacy programs, government healthcare benefits, "
        "housing or utilities, cellular or telecommunications, internet access, "
        "and newcomer-friendly essential programs. "
        "Group recommendations by category. Include official URLs when supported, signup "
        "steps, fees or credit checks, eligibility caveats, confidence, and a final "
        "compliance review that avoids legal, medical, or financial advice."
    )


def _content_text_from_event(event: dict[str, Any]) -> str:
    content = event.get("content") or {}
    parts = content.get("parts") or []
    text_parts: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            text_parts.append(str(part["text"]))
    return "\n".join(text_parts).strip()


def _extract_agent_artifacts(events: list[dict[str, Any]]) -> dict[str, Any]:
    final_text = ""
    plan: dict[str, Any] | None = None
    redactions: list[str] = []
    interruption_messages: list[str] = []
    errors: list[str] = []

    for event in events:
        output = event.get("output")
        if isinstance(output, dict):
            if "recommendations" in output and "opening_summary" in output:
                plan = output
            redactions.extend(output.get("redaction_categories") or [])
            if output.get("reason") and output.get("action"):
                interruption_messages.append(str(output["reason"]))
        elif isinstance(output, str) and output.strip():
            final_text = output.strip()

        text = _content_text_from_event(event)
        if text:
            final_text = text
            if "Security checkpoint routed" in text or "Missing:" in text:
                interruption_messages.append(text)

        if event.get("error_message"):
            errors.append(str(event["error_message"]))

    return {
        "final_text": final_text,
        "plan": plan,
        "redactions": sorted(set(redactions)),
        "interruption_messages": interruption_messages,
        "errors": errors,
        "event_count": len(events),
    }


async def _invoke_local_backend_agent(prompt: str) -> dict[str, Any]:
    if not BACKEND_ROOT.exists():
        raise RuntimeError(f"Backend directory not found at {BACKEND_ROOT}")

    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))

    # Local dashboard runs should use the ADK in-memory runner services. The model
    # provider still comes from newcomer-agent/app/.env or the caller environment.
    if os.environ.get("SUBMISSION_FRONTEND_USE_VERTEX_RUNTIME") != "1":
        os.environ.setdefault("INTEGRATION_TEST", "TRUE")

    from app.agent_runtime_app import get_agent_runtime  # type: ignore

    global _agent_runtime_ready
    runtime = get_agent_runtime()
    async with _agent_runtime_lock:
        if not _agent_runtime_ready:
            runtime.set_up()
            _agent_runtime_ready = True

    events: list[dict[str, Any]] = []
    user_id = f"submission-dashboard-{uuid.uuid4().hex[:10]}"
    async for event in runtime.async_stream_query(message=prompt, user_id=user_id):
        if hasattr(event, "model_dump"):
            events.append(event.model_dump(mode="json"))
        else:
            events.append(dict(event))

    artifacts = _extract_agent_artifacts(events)
    artifacts["raw_events"] = events
    return artifacts


def _normalize_recommendation(item: dict[str, Any], index: int) -> dict[str, Any]:
    category = str(item.get("category") or "General essentials").strip()
    confidence = str(item.get("confidence") or "medium").strip().lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"

    signup = item.get("signup_instructions") or item.get("signup") or []
    if isinstance(signup, str):
        signup = [signup]

    return {
        "id": f"rec-{index}-{uuid.uuid4().hex[:6]}",
        "program_name": str(item.get("program_name") or "Local program to verify").strip(),
        "provider": str(item.get("provider") or "Local provider").strip(),
        "category": category,
        "why_recommended": str(item.get("why_recommended") or item.get("why") or "").strip(),
        "eligibility_notes": str(item.get("eligibility_notes") or "Verify on the official page.").strip(),
        "signup_instructions": [str(step).strip() for step in signup if str(step).strip()],
        "official_url": str(item.get("official_url") or item.get("source_url") or "").strip(),
        "cost_or_fees": str(item.get("cost_or_fees") or "Verify before signing up.").strip(),
        "confidence": confidence,
        "caution_notes": str(item.get("caution_notes") or "").strip(),
    }


def _section_after_heading(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    capture = False
    captured: list[str] = []
    for line in lines:
        if line.strip().lower() == heading.lower():
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            captured.append(line)
    return captured


def _parse_markdown_plan(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    opening_lines: list[str] = []
    for line in lines:
        if line.startswith("## "):
            break
        if line.strip():
            opening_lines.append(line.strip())

    context = "\n".join(_section_after_heading(text, "## Context used")).strip()
    priority_lines = [line.strip() for line in _section_after_heading(text, "## Priority areas") if line.strip()]
    priorities: list[str] = []
    if priority_lines:
        priorities = [part.strip() for part in priority_lines[0].split(",") if part.strip()]

    recommendations: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_signup = False
    header_re = re.compile(r"^\s*\d+\.\s+\*\*(.+?)\*\*\s+-\s+(.+?)\s*$")
    field_re = re.compile(r"^\s*-\s+([^:]+):\s*(.*)$")
    signup_re = re.compile(r"^\s*\d+\.\s+(.*)$")

    for raw_line in _section_after_heading(text, "## Recommended programs"):
        line = raw_line.rstrip()
        header_match = header_re.match(line)
        if header_match:
            if current:
                recommendations.append(current)
            current = {
                "program_name": header_match.group(1).strip(),
                "provider": header_match.group(2).strip(),
                "signup_instructions": [],
            }
            in_signup = False
            continue

        if not current:
            continue

        field_match = field_re.match(line)
        if field_match:
            key = field_match.group(1).strip().lower()
            value = field_match.group(2).strip()
            in_signup = key == "signup"
            if key == "category":
                current["category"] = value
            elif key == "why it fits":
                current["why_recommended"] = value
            elif key == "eligibility":
                current["eligibility_notes"] = value
            elif key == "fees/checks":
                current["cost_or_fees"] = value
            elif key == "link" and not value.lower().startswith("no official"):
                current["official_url"] = value
            elif key == "confidence":
                current["confidence"] = value
            elif key == "note":
                current["caution_notes"] = value
            continue

        if in_signup:
            signup_match = signup_re.match(line.strip())
            if signup_match:
                current.setdefault("signup_instructions", []).append(signup_match.group(1).strip())

    if current:
        recommendations.append(current)

    next_steps = [
        re.sub(r"^\s*-\s*", "", line).strip()
        for line in _section_after_heading(text, "## Next steps")
        if line.strip()
    ]

    return {
        "opening_summary": " ".join(opening_lines).strip(),
        "comparison_context_used": context,
        "priority_categories": priorities,
        "recommendations": recommendations,
        "next_steps": next_steps,
        "disclaimer": _infer_disclaimer(text),
    }


def _infer_disclaimer(text: str) -> str:
    candidates = [
        line.strip()
        for line in text.splitlines()
        if "not legal" in line.lower()
        or "not financial" in line.lower()
        or "not medical" in line.lower()
        or "verify" in line.lower()
    ]
    return candidates[-1] if candidates else "Verify eligibility, fees, and signup terms on official provider pages."


def _category_accent(category: str) -> str:
    palette = [
        "#0f766e",
        "#c2410c",
        "#7c3aed",
        "#be123c",
        "#2563eb",
        "#4d7c0f",
        "#a16207",
        "#0e7490",
    ]
    return palette[abs(hash(category)) % len(palette)]


def _group_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for recommendation in recommendations:
        grouped[recommendation.get("category") or "General essentials"].append(recommendation)

    categories: list[dict[str, Any]] = []
    for category, items in grouped.items():
        categories.append(
            {
                "name": category,
                "accent": _category_accent(category),
                "count": len(items),
                "items": items,
            }
        )
    return categories


def _shape_agent_response(
    intake: NewcomerIntake,
    artifacts: dict[str, Any],
    *,
    mode: str,
    backend_error_detail: str | None = None,
) -> dict[str, Any]:
    plan = artifacts.get("plan") or _parse_markdown_plan(artifacts.get("final_text") or "")
    recommendations = [
        _normalize_recommendation(item, index)
        for index, item in enumerate(plan.get("recommendations") or [], start=1)
    ]

    categories = _group_recommendations(recommendations)
    destination = _clean_location(intake.destination_location)
    origin = _clean_location(intake.origin_location)
    disclaimer = str(plan.get("disclaimer") or "").strip()
    priority_categories = plan.get("priority_categories") or [
        category["name"] for category in categories
    ]
    comparison_context = plan.get("comparison_context_used") or ""
    destination_theme = _destination_theme(
        destination,
        comparison_context,
        [str(category) for category in priority_categories],
    )
    destination_summary = _destination_summary(
        origin,
        destination,
        comparison_context,
        [str(category) for category in priority_categories],
        intake.family_size,
    )

    return {
        "profile": {
            "age": intake.age,
            "family_size": intake.family_size,
            "origin_location": origin,
            "destination_location": destination,
            "origin_country": origin,
            "destination_country": destination,
        },
        "agent_mode": mode,
        "opening_summary": plan.get("opening_summary")
        or f"Here is a practical first-pass rewards plan for settling in {destination}.",
        "comparison_context": comparison_context,
        "destination_theme": destination_theme,
        "destination_summary": destination_summary,
        "priority_categories": priority_categories,
        "categories": categories,
        "next_steps": plan.get("next_steps") or [
            "Confirm eligibility and fees on official provider pages.",
            "Start with no-fee or public-service options before paid memberships.",
            "Keep a simple note of programs worth reviewing with the newcomer.",
        ],
        "welcome": {
            "title": f"Welcome to {destination}",
            "notes": [
                f"Your plan starts with everyday comfort in {destination}: food, movement, money setup, and health basics.",
                f"Household size is included so the agent can weigh shared essentials for {intake.family_size} people.",
                "No passport number, immigration ID, phone number, or home address was collected here.",
                f"Your {origin} context helps the agent explain differences without making assumptions about your story.",
            ],
        },
        "compliance_review": {
            "title": "Final compliance review",
            "status": "Ready for manager review" if mode == "backend_agent" else "Backend agent issue",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "summary": disclaimer or "Recommendations are informational and should be verified on official pages.",
            "checks": [
                "Sensitive identity fields were not requested by this dashboard.",
                "Eligibility, fees, credit checks, and uncertainty are kept visible for manager review.",
                "Recommendations should not be treated as legal, medical, or financial advice.",
                "Official provider pages should be used before a newcomer enrolls.",
            ],
            "agent_notes": artifacts.get("interruption_messages") or [],
            "redactions": artifacts.get("redactions") or ["No sensitive identifiers were submitted."],
            "event_count": artifacts.get("event_count", 0),
            "backend_error_detail": backend_error_detail,
        },
        "raw_agent_text": artifacts.get("final_text") or "",
    }


async def _recommendations_from_agent(intake: NewcomerIntake) -> dict[str, Any]:
    prompt = _build_agent_prompt(intake)
    timeout_seconds = _agent_timeout_seconds()
    try:
        artifacts = await asyncio.wait_for(
            _invoke_local_backend_agent(prompt),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        raise BackendAgentTimeoutError(timeout_seconds) from exc

    response = _shape_agent_response(intake, artifacts, mode="backend_agent")
    if not response["categories"]:
        raise RuntimeError("Backend agent did not return parseable recommendations.")
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "backend_found": BACKEND_ROOT.exists(),
        "backend_root": str(BACKEND_ROOT),
    }


@app.get("/api/location-suggestions")
async def location_suggestions(q: str = "") -> dict[str, Any]:
    query = _clean_location(q)
    suggestions = await asyncio.to_thread(_fetch_location_suggestions, query, 8)
    return {"query": query, "suggestions": suggestions}


@app.post("/api/recommendations")
async def recommendations(intake: NewcomerIntake) -> JSONResponse:
    normalized = NewcomerIntake(
        age=intake.age,
        family_size=intake.family_size,
        origin_location=_clean_location(intake.origin_location),
        destination_location=_clean_location(intake.destination_location),
    )
    start = time.perf_counter()
    try:
        response = await _recommendations_from_agent(normalized)
    except BackendAgentTimeoutError as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        return JSONResponse(
            status_code=504,
            content={
                "error": "backend_agent_timeout",
                "message": (
                    "The newcomer-agent backend took longer than "
                    f"{_format_seconds(exc.timeout_seconds)} to return dynamic "
                    "recommendations."
                ),
                "detail": str(exc),
                "latency_ms": elapsed_ms,
                "suggested_fixes": [
                    "Increase SUBMISSION_FRONTEND_AGENT_TIMEOUT for local demo runs.",
                    "Use a faster or higher-quota model for the multi-step ADK workflow.",
                    "Reduce model calls by making profile extraction, customization, or recommendation packaging more deterministic.",
                    "Check server logs for Gemini quota, model high-demand retries, or slow search grounding.",
                ],
            },
        )
    except Exception as exc:  # Keep the dashboard useful during local credential gaps.
        return JSONResponse(
            status_code=502,
            content={
                "error": "backend_agent_unavailable",
                "message": (
                    "The newcomer-agent backend did not return dynamic recommendations. "
                    "Check API credentials, model access, search access, and server logs."
                ),
                "detail": f"{type(exc).__name__}: {exc}",
            },
        )

    response["latency_ms"] = round((time.perf_counter() - start) * 1000)
    return JSONResponse(response)


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Newcomer Rewards Manager</title>
  <style>
    :root {
      --ink: #17202a;
      --muted: #647078;
      --paper: #fffefd;
      --wash: #f5faf7;
      --line: #dfe8e2;
      --teal: #0f766e;
      --coral: #c2410c;
      --violet: #6d28d9;
      --gold: #a16207;
      --blue: #2563eb;
      --theme-primary: #0f766e;
      --theme-secondary: #f59e0b;
      --theme-accent: #2563eb;
      --theme-soft: #effaf5;
      --destination-image: none;
      --shadow: 0 18px 60px rgba(23, 32, 42, 0.13);
      --radius: 8px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        linear-gradient(120deg, color-mix(in srgb, var(--theme-primary) 15%, transparent), transparent 28%),
        linear-gradient(240deg, color-mix(in srgb, var(--theme-secondary) 14%, transparent), transparent 32%),
        linear-gradient(180deg, #f8fcfb 0%, #fffaf4 48%, #f1f7ff 100%);
      transition: background 420ms ease, color 240ms ease;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(15, 118, 110, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(37, 99, 235, 0.05) 1px, transparent 1px);
      background-size: 46px 46px;
      mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.75), transparent 80%);
      z-index: 0;
    }

    body::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(180deg, rgba(248, 252, 251, 0.74), rgba(255, 250, 244, 0.84)),
        var(--destination-image);
      background-position: center;
      background-size: cover;
      opacity: 0;
      transition: opacity 520ms ease;
      z-index: 0;
    }

    body.has-destination-image::after {
      opacity: 0.42;
    }

    button, input { font: inherit; }

    .shell {
      width: min(1280px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 56px;
      position: relative;
      z-index: 1;
    }

    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      margin-bottom: 28px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .brand-mark {
      width: 42px;
      height: 42px;
      border-radius: var(--radius);
      background:
        linear-gradient(135deg, var(--teal), #46a094 52%, #f6c56b 52%, var(--coral));
      box-shadow: 0 12px 30px rgba(15, 118, 110, 0.24);
      position: relative;
      flex: 0 0 auto;
    }

    .brand-mark::after {
      content: "";
      position: absolute;
      width: 18px;
      height: 18px;
      border: 2px solid #fff;
      border-left: 0;
      border-bottom: 0;
      transform: rotate(45deg);
      top: 12px;
      left: 9px;
    }

    .brand h1 {
      font-size: clamp(1.32rem, 2vw, 2rem);
      line-height: 1.05;
      margin: 0;
      font-weight: 850;
      letter-spacing: 0;
    }

    .brand p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.96rem;
    }

    .status-strip {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .chip {
      border: 1px solid rgba(23, 32, 42, 0.11);
      background: rgba(255, 255, 255, 0.72);
      padding: 8px 10px;
      border-radius: var(--radius);
      color: #34414a;
      font-size: 0.88rem;
      backdrop-filter: blur(16px);
    }

    .workspace {
      display: grid;
      grid-template-columns: 390px minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }

    .intake-panel {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid rgba(23, 32, 42, 0.10);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
      position: sticky;
      top: 18px;
      transition: transform 260ms ease, box-shadow 260ms ease;
    }

    .intake-panel:hover {
      transform: translateY(-2px);
    }

    .postcard {
      padding: 22px;
      color: #fff;
      background:
        linear-gradient(135deg, color-mix(in srgb, var(--theme-primary) 92%, #111827), color-mix(in srgb, var(--theme-accent) 82%, #ffffff)),
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.24), transparent 34%);
      min-height: 170px;
      position: relative;
      overflow: hidden;
    }

    .postcard::after {
      content: "";
      position: absolute;
      right: 18px;
      bottom: 16px;
      width: 120px;
      height: 74px;
      background:
        linear-gradient(to top, rgba(255,255,255,0.22) 0 18px, transparent 18px),
        linear-gradient(135deg, transparent 0 36%, rgba(255,255,255,0.26) 36% 48%, transparent 48%),
        linear-gradient(45deg, transparent 0 45%, rgba(255,255,255,0.18) 45% 56%, transparent 56%);
      border-bottom: 3px solid rgba(255, 255, 255, 0.45);
      opacity: 0.9;
    }

    .eyebrow {
      text-transform: uppercase;
      font-size: 0.74rem;
      font-weight: 800;
      letter-spacing: 0;
      opacity: 0.82;
      margin: 0 0 12px;
    }

    .postcard h2 {
      font-size: 1.85rem;
      line-height: 1.1;
      max-width: 280px;
      margin: 0 0 10px;
      letter-spacing: 0;
    }

    .postcard p {
      max-width: 285px;
      margin: 0;
      line-height: 1.5;
      opacity: 0.9;
    }

    form {
      padding: 20px;
      display: grid;
      gap: 15px;
    }

    .journey-tabs {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      padding: 14px 20px 0;
    }

    .journey-tab {
      min-height: 42px;
      border: 1px solid rgba(23, 32, 42, 0.10);
      border-radius: var(--radius);
      background: #fff;
      color: #53616a;
      font-weight: 820;
      transition: background 180ms ease, color 180ms ease, transform 180ms ease;
    }

    .journey-tab.is-active {
      background: var(--theme-soft);
      color: var(--theme-primary);
      transform: translateY(-1px);
    }

    .form-screen {
      display: none;
      gap: 15px;
      animation: riseIn 220ms ease both;
    }

    .form-screen.is-active {
      display: grid;
    }

    .form-actions {
      display: grid;
      grid-template-columns: 1fr 1.4fr;
      gap: 8px;
    }

    label {
      display: grid;
      gap: 7px;
      color: #2b3740;
      font-weight: 740;
      font-size: 0.94rem;
    }

    input {
      width: 100%;
      min-height: 48px;
      border: 1px solid #ccd9d2;
      border-radius: var(--radius);
      background: #fff;
      padding: 12px 13px;
      color: var(--ink);
      outline: 0;
      transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
    }

    input:focus {
      border-color: var(--theme-primary);
      box-shadow: 0 0 0 4px color-mix(in srgb, var(--theme-primary) 18%, transparent);
      transform: translateY(-1px);
    }

    .suggestion-wrap {
      display: block;
      position: relative;
    }

    .suggestion-menu {
      position: absolute;
      left: 0;
      right: 0;
      top: calc(100% + 7px);
      z-index: 18;
      display: none;
      max-height: 245px;
      overflow: auto;
      border: 1px solid rgba(23, 32, 42, 0.13);
      border-radius: var(--radius);
      background: rgba(255, 255, 255, 0.98);
      box-shadow: 0 18px 42px rgba(23, 32, 42, 0.16);
      padding: 6px;
    }

    .suggestion-menu.is-open {
      display: grid;
      gap: 4px;
      animation: popIn 150ms ease both;
    }

    .suggestion-option {
      border: 0;
      border-radius: var(--radius);
      background: transparent;
      color: #26323a;
      cursor: pointer;
      min-height: 42px;
      padding: 9px 10px;
      text-align: left;
      transition: background 150ms ease, transform 150ms ease;
    }

    .suggestion-option:hover,
    .suggestion-option.is-highlighted {
      background: var(--theme-soft);
      transform: translateX(2px);
    }

    .suggestion-option small {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      line-height: 1.3;
    }

    .secondary-button {
      min-height: 48px;
      border: 1px solid rgba(23, 32, 42, 0.12);
      border-radius: var(--radius);
      background: #fff;
      cursor: pointer;
      color: #25313a;
      font-weight: 820;
      transition: transform 150ms ease, border-color 150ms ease, background 150ms ease;
    }

    .secondary-button:hover {
      transform: translateY(-1px);
      border-color: color-mix(in srgb, var(--theme-primary) 40%, #dfe8e2);
      background: var(--theme-soft);
    }

    .comfort-list {
      display: grid;
      gap: 8px;
      margin: 2px 0 4px;
    }

    .comfort-item {
      display: flex;
      gap: 9px;
      align-items: center;
      color: #4b5962;
      font-size: 0.9rem;
      line-height: 1.35;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 99px;
      background: var(--coral);
      box-shadow: 0 0 0 5px rgba(194, 65, 12, 0.10);
      flex: 0 0 auto;
    }

    .primary-button, .review-button {
      border: 0;
      border-radius: var(--radius);
      cursor: pointer;
      transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      min-height: 48px;
      font-weight: 820;
    }

    .primary-button {
      color: #fff;
      background: linear-gradient(135deg, var(--theme-primary), var(--theme-accent));
      box-shadow: 0 14px 28px color-mix(in srgb, var(--theme-primary) 25%, transparent);
    }

    .primary-button:hover, .review-button:hover { transform: translateY(-1px); }
    .primary-button:disabled { cursor: wait; opacity: 0.78; transform: none; }

    .results-area {
      min-width: 0;
      animation: riseIn 260ms ease both;
    }

    body.has-results .intake-panel {
      box-shadow: 0 18px 54px color-mix(in srgb, var(--theme-primary) 18%, transparent);
    }

    .welcome-band {
      border: 1px solid rgba(23, 32, 42, 0.10);
      background: rgba(255, 255, 255, 0.76);
      border-radius: var(--radius);
      padding: 20px;
      margin-bottom: 18px;
      box-shadow: 0 12px 38px rgba(23, 32, 42, 0.08);
      position: relative;
      overflow: hidden;
    }

    .welcome-band::after {
      content: "";
      position: absolute;
      right: 18px;
      bottom: -2px;
      width: 190px;
      height: 62px;
      background:
        linear-gradient(to top, color-mix(in srgb, var(--theme-primary) 24%, transparent) 0 12px, transparent 12px),
        linear-gradient(135deg, transparent 0 42%, color-mix(in srgb, var(--theme-accent) 22%, transparent) 42% 54%, transparent 54%);
      opacity: 0.9;
      pointer-events: none;
    }

    .welcome-band h2 {
      margin: 0 0 8px;
      font-size: clamp(1.35rem, 2vw, 2.1rem);
      letter-spacing: 0;
    }

    .welcome-band p {
      margin: 0;
      color: #4e5b64;
      line-height: 1.55;
    }

    .progress-rail {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-bottom: 18px;
    }

    .city-summary {
      border: 1px solid rgba(23, 32, 42, 0.10);
      background:
        linear-gradient(135deg, color-mix(in srgb, var(--theme-soft) 82%, #fff), #ffffff 72%),
        linear-gradient(90deg, color-mix(in srgb, var(--theme-primary) 10%, transparent), transparent);
      border-radius: var(--radius);
      padding: 18px;
      margin-bottom: 18px;
      display: grid;
      gap: 12px;
      box-shadow: 0 12px 32px rgba(23, 32, 42, 0.07);
      animation: riseIn 260ms ease both;
    }

    .city-summary h3 {
      margin: 0;
      font-size: 1.08rem;
      letter-spacing: 0;
    }

    .city-summary p {
      margin: 0;
      color: #4e5b64;
      line-height: 1.55;
    }

    .city-summary-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .city-summary-tile {
      border: 1px solid rgba(23, 32, 42, 0.09);
      border-radius: var(--radius);
      background: rgba(255, 255, 255, 0.72);
      padding: 11px;
      min-height: 82px;
    }

    .city-summary-tile span {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 820;
      text-transform: uppercase;
      margin-bottom: 5px;
    }

    .city-summary-tile strong {
      display: block;
      color: #27333b;
      font-size: 0.92rem;
      line-height: 1.35;
    }

    .step {
      border: 1px solid rgba(23, 32, 42, 0.10);
      background: rgba(255, 255, 255, 0.70);
      border-radius: var(--radius);
      padding: 12px;
      color: #59666f;
      min-height: 72px;
      transition: transform 220ms ease, border-color 220ms ease, background 220ms ease;
    }

    .step strong {
      display: block;
      color: #27333b;
      margin-bottom: 4px;
    }

    .step.is-active {
      border-color: rgba(15, 118, 110, 0.35);
      background: #f0fbf7;
      transform: translateY(-2px);
    }

    .toolbar {
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: center;
      margin-bottom: 16px;
    }

    .toolbar h2 {
      font-size: 1.2rem;
      margin: 0;
      letter-spacing: 0;
    }

    .toolbar p {
      margin: 4px 0 0;
      color: var(--muted);
      font-size: 0.93rem;
    }

    .review-button {
      color: #fff;
      background: #17202a;
      padding: 0 15px;
      white-space: nowrap;
    }

    .category-stack {
      display: grid;
      gap: 22px;
    }

    .category-block {
      display: grid;
      gap: 12px;
      animation: riseIn 260ms ease both;
    }

    .category-heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding-left: 13px;
      border-left: 5px solid var(--accent, var(--teal));
    }

    .category-heading h3 {
      margin: 0;
      font-size: 1.1rem;
      letter-spacing: 0;
    }

    .category-heading span {
      color: var(--muted);
      font-size: 0.9rem;
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .rec-card {
      border: 1px solid rgba(23, 32, 42, 0.10);
      background: rgba(255, 255, 255, 0.88);
      border-radius: var(--radius);
      padding: 16px;
      min-height: 285px;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 12px;
      box-shadow: 0 12px 28px rgba(23, 32, 42, 0.08);
      transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
      position: relative;
      overflow: hidden;
    }

    .rec-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 18px 42px rgba(23, 32, 42, 0.12);
      border-color: rgba(15, 118, 110, 0.26);
    }

    .rec-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }

    .rec-card h4 {
      margin: 0 0 4px;
      font-size: 1rem;
      line-height: 1.25;
      letter-spacing: 0;
    }

    .provider {
      color: var(--muted);
      font-size: 0.9rem;
      line-height: 1.35;
    }

    .confidence {
      border: 1px solid rgba(23, 32, 42, 0.10);
      border-radius: var(--radius);
      padding: 6px 8px;
      font-size: 0.76rem;
      color: #30404a;
      background: #f8fbf9;
      text-transform: uppercase;
      font-weight: 840;
      white-space: nowrap;
    }

    .rec-body {
      display: grid;
      gap: 9px;
      color: #46535d;
      font-size: 0.93rem;
      line-height: 1.46;
    }

    .mini-label {
      display: block;
      font-weight: 820;
      color: #27333b;
      margin-bottom: 2px;
    }

    .signup-list {
      margin: 0;
      padding-left: 18px;
    }

    .signup-list li { margin-bottom: 4px; }

    .spinner {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      border: 2px solid rgba(255, 255, 255, 0.55);
      border-top-color: #fff;
      display: inline-block;
      animation: spin 850ms linear infinite;
    }

    .empty-state {
      border: 1px dashed rgba(23, 32, 42, 0.18);
      border-radius: var(--radius);
      min-height: 470px;
      display: grid;
      place-items: center;
      text-align: center;
      padding: 34px;
      background: rgba(255, 255, 255, 0.55);
    }

    .empty-state h2 {
      margin: 0 0 10px;
      font-size: 1.5rem;
      letter-spacing: 0;
    }

    .empty-state p {
      max-width: 560px;
      margin: 0 auto;
      color: var(--muted);
      line-height: 1.55;
    }

    .toast {
      position: fixed;
      left: 50%;
      bottom: 24px;
      transform: translateX(-50%) translateY(24px);
      background: #17202a;
      color: #fff;
      padding: 12px 14px;
      border-radius: var(--radius);
      opacity: 0;
      pointer-events: none;
      transition: opacity 180ms ease, transform 180ms ease;
      z-index: 20;
      box-shadow: var(--shadow);
    }

    .toast.is-visible {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }

    .drawer-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(23, 32, 42, 0.32);
      opacity: 0;
      pointer-events: none;
      transition: opacity 220ms ease;
      z-index: 30;
    }

    .drawer {
      position: fixed;
      top: 0;
      right: 0;
      height: 100vh;
      width: min(520px, 100%);
      background: var(--paper);
      box-shadow: -22px 0 56px rgba(23, 32, 42, 0.24);
      transform: translateX(104%);
      transition: transform 260ms ease;
      z-index: 31;
      display: grid;
      grid-template-rows: auto 1fr;
    }

    body.drawer-open .drawer-backdrop {
      opacity: 1;
      pointer-events: auto;
    }

    body.drawer-open .drawer { transform: translateX(0); }

    .drawer-header {
      padding: 22px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 14px;
    }

    .drawer-header h2 {
      margin: 0 0 5px;
      letter-spacing: 0;
    }

    .drawer-header p {
      margin: 0;
      color: var(--muted);
    }

    .close-button {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      width: 40px;
      height: 40px;
      background: #fff;
      cursor: pointer;
      font-size: 1.2rem;
    }

    .drawer-body {
      padding: 22px;
      overflow: auto;
      display: grid;
      gap: 18px;
    }

    .review-section {
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 14px;
      background: #fbfefd;
    }

    .review-section h3 {
      margin: 0 0 10px;
      font-size: 0.98rem;
      letter-spacing: 0;
    }

    .review-section p, .review-section li {
      color: #4d5a63;
      line-height: 1.5;
      font-size: 0.93rem;
    }

    .review-section ul {
      margin: 0;
      padding-left: 18px;
    }

    [hidden] { display: none !important; }

    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes riseIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes popIn {
      from { opacity: 0; transform: translateY(-5px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @media (max-width: 980px) {
      .workspace { grid-template-columns: 1fr; }
      .intake-panel { position: relative; top: 0; }
      .cards { grid-template-columns: 1fr; }
      .progress-rail { grid-template-columns: 1fr; }
    }

    @media (max-width: 620px) {
      .shell { width: min(100% - 20px, 1280px); padding-top: 16px; }
      .topbar, .toolbar { align-items: flex-start; flex-direction: column; }
      .status-strip { justify-content: flex-start; }
      .postcard h2 { font-size: 1.55rem; }
      .city-summary-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true"></div>
        <div>
          <h1>Newcomer Rewards Manager</h1>
          <p>Friendly essential-program review for a softer landing.</p>
        </div>
      </div>
      <div class="status-strip" aria-label="Dashboard safeguards">
        <span class="chip">No sensitive IDs</span>
        <span class="chip">Agent-reviewed</span>
        <span class="chip">Compliance review</span>
      </div>
    </header>

    <main class="workspace">
      <aside class="intake-panel">
        <div class="postcard">
          <p class="eyebrow">New arrival intake</p>
          <h2 id="postcardTitle">A calm first step</h2>
          <p id="postcardCopy">Start with the essentials that make a new place feel navigable: food, transit, banking, phone access, health, and community.</p>
        </div>
        <div class="journey-tabs" aria-label="Intake steps">
          <button class="journey-tab is-active" data-step-target="profile" type="button">Profile</button>
          <button class="journey-tab" data-step-target="places" type="button">Places</button>
        </div>
        <form id="intakeForm" novalidate>
          <section class="form-screen is-active" data-form-screen="profile">
            <label>
              Age
              <input id="age" name="age" type="number" min="1" max="120" inputmode="numeric" placeholder="34" required>
            </label>
            <label>
              Family size
              <input id="familySize" name="familySize" type="number" min="1" max="20" inputmode="numeric" placeholder="3" required>
            </label>
            <div class="comfort-list">
              <div class="comfort-item"><span class="dot"></span><span>Daily essentials are weighted for the whole household.</span></div>
              <div class="comfort-item"><span class="dot"></span><span>No sensitive identity fields are part of this intake.</span></div>
            </div>
            <button class="primary-button" id="nextPlaces" type="button">Next: places</button>
          </section>

          <section class="form-screen" data-form-screen="places">
            <label>
              Origin location
              <span class="suggestion-wrap">
                <input id="origin" name="origin" autocomplete="off" placeholder="Neighborhood, city, region, or country" aria-autocomplete="list" aria-expanded="false" required>
                <span class="suggestion-menu" id="originSuggestionMenu" role="listbox"></span>
              </span>
            </label>
            <label>
              Destination location
              <span class="suggestion-wrap">
                <input id="destination" name="destination" autocomplete="off" placeholder="Neighborhood, city, region, or country" aria-autocomplete="list" aria-expanded="false" required>
                <span class="suggestion-menu" id="destinationSuggestionMenu" role="listbox"></span>
              </span>
            </label>
            <div class="comfort-list">
              <div class="comfort-item"><span class="dot"></span><span>Every recommendation keeps newcomer uncertainty visible.</span></div>
              <div class="comfort-item"><span class="dot"></span><span>Programs are sorted around daily comfort, not paperwork pressure.</span></div>
              <div class="comfort-item"><span class="dot"></span><span>Use any location wording that feels natural; no home address needed.</span></div>
            </div>
            <div class="form-actions">
              <button class="secondary-button" id="backProfile" type="button">Back</button>
              <button class="primary-button" id="submitButton" type="submit">
                <span class="button-text">Find welcoming rewards</span>
                <span class="spinner" hidden></span>
              </button>
            </div>
          </section>
        </form>
      </aside>

      <section class="results-area">
        <section class="empty-state" id="emptyState">
          <div>
            <h2>Ready when they are.</h2>
            <p>The recommendation queue will appear here by category, with warm welcome notes, eligibility summaries, signup steps, and compliance review.</p>
          </div>
        </section>

        <section id="results" hidden>
          <div class="welcome-band">
            <h2 id="welcomeTitle">Welcome</h2>
            <p id="welcomeNotes"></p>
          </div>

          <div class="progress-rail" aria-label="Agent progress">
            <div class="step" data-step="intake"><strong>Profile</strong><span>Age, family size, locations</span></div>
            <div class="step" data-step="agent"><strong>Agent match</strong><span>Local program reasoning</span></div>
            <div class="step" data-step="review"><strong>Review</strong><span>Compliance notes ready</span></div>
          </div>

          <section class="city-summary" id="citySummary" aria-labelledby="citySummaryTitle">
            <div>
              <h3 id="citySummaryTitle">Destination snapshot</h3>
              <p id="citySummaryText"></p>
            </div>
            <div class="city-summary-grid">
              <div class="city-summary-tile"><span>Local focus</span><strong id="citySummaryFocus"></strong></div>
              <div class="city-summary-tile"><span>Household lens</span><strong id="citySummaryHousehold"></strong></div>
            </div>
          </section>

          <div class="toolbar">
            <div>
              <h2>Recommendation queue</h2>
              <p id="queueSummary">Programs grouped by category.</p>
            </div>
            <button class="review-button" id="openReview" type="button">Compliance review</button>
          </div>

          <div class="category-stack" id="categoryStack"></div>
        </section>
      </section>
    </main>
  </div>

  <div class="drawer-backdrop" id="drawerBackdrop"></div>
  <aside class="drawer" id="reviewDrawer" aria-hidden="true" aria-labelledby="reviewTitle">
    <div class="drawer-header">
      <div>
        <h2 id="reviewTitle">Final compliance review</h2>
        <p id="reviewStatus">Awaiting recommendations</p>
      </div>
      <button class="close-button" id="closeReview" type="button" aria-label="Close review">x</button>
    </div>
    <div class="drawer-body" id="reviewBody"></div>
  </aside>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>

  <script>
    const form = document.querySelector("#intakeForm");
    const submitButton = document.querySelector("#submitButton");
    const submitText = submitButton.querySelector(".button-text");
    const submitSpinner = submitButton.querySelector(".spinner");
    const ageInput = document.querySelector("#age");
    const familySizeInput = document.querySelector("#familySize");
    const formScreens = [...document.querySelectorAll("[data-form-screen]")];
    const journeyTabs = [...document.querySelectorAll("[data-step-target]")];
    const nextPlaces = document.querySelector("#nextPlaces");
    const backProfile = document.querySelector("#backProfile");
    const emptyState = document.querySelector("#emptyState");
    const results = document.querySelector("#results");
    const categoryStack = document.querySelector("#categoryStack");
    const queueSummary = document.querySelector("#queueSummary");
    const welcomeTitle = document.querySelector("#welcomeTitle");
    const welcomeNotes = document.querySelector("#welcomeNotes");
    const citySummaryTitle = document.querySelector("#citySummaryTitle");
    const citySummaryText = document.querySelector("#citySummaryText");
    const citySummaryFocus = document.querySelector("#citySummaryFocus");
    const citySummaryHousehold = document.querySelector("#citySummaryHousehold");
    const toast = document.querySelector("#toast");
    const reviewDrawer = document.querySelector("#reviewDrawer");
    const reviewBody = document.querySelector("#reviewBody");
    const reviewStatus = document.querySelector("#reviewStatus");
    const originInput = document.querySelector("#origin");
    const destinationInput = document.querySelector("#destination");
    const originSuggestionMenu = document.querySelector("#originSuggestionMenu");
    const destinationSuggestionMenu = document.querySelector("#destinationSuggestionMenu");
    const postcardTitle = document.querySelector("#postcardTitle");
    const postcardCopy = document.querySelector("#postcardCopy");

    let latestResponse = null;
    let toastTimer = null;

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function showToast(message) {
      toast.textContent = message;
      toast.classList.add("is-visible");
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 2200);
    }

    function setLoading(isLoading) {
      submitButton.disabled = isLoading;
      nextPlaces.disabled = isLoading;
      backProfile.disabled = isLoading;
      submitText.textContent = isLoading ? "Asking the agents..." : "Find welcoming rewards";
      submitSpinner.hidden = !isLoading;
      document.querySelectorAll(".step").forEach((step) => step.classList.toggle("is-active", isLoading));
    }

    function showFormScreen(name) {
      formScreens.forEach((screen) => {
        screen.classList.toggle("is-active", screen.dataset.formScreen === name);
      });
      journeyTabs.forEach((tab) => {
        tab.classList.toggle("is-active", tab.dataset.stepTarget === name);
      });
    }

    function profileFieldsValid() {
      if (!ageInput.reportValidity()) return false;
      if (!familySizeInput.reportValidity()) return false;
      return true;
    }

    nextPlaces.addEventListener("click", () => {
      if (profileFieldsValid()) showFormScreen("places");
    });

    backProfile.addEventListener("click", () => showFormScreen("profile"));

    journeyTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        if (tab.dataset.stepTarget === "profile" || profileFieldsValid()) {
          showFormScreen(tab.dataset.stepTarget);
        }
      });
    });

    function closeSuggestionMenu(input, menu) {
      menu.classList.remove("is-open");
      menu.innerHTML = "";
      input.setAttribute("aria-expanded", "false");
    }

    function renderSuggestionMenu(input, menu, suggestions) {
      const cleanSuggestions = (suggestions || []).filter((suggestion) => suggestion && suggestion.value);
      if (!cleanSuggestions.length) {
        closeSuggestionMenu(input, menu);
        return;
      }

      menu.innerHTML = cleanSuggestions.map((suggestion, index) => {
        const sourceLabel = suggestion.source === "typed"
          ? "Use this location"
          : suggestion.source === "local"
            ? "Helpful local match"
            : "City suggestion";
        return `
          <button class="suggestion-option" data-value="${escapeHtml(suggestion.value)}" id="${input.id}-suggestion-${index}" role="option" type="button">
            <span>${escapeHtml(suggestion.value)}</span>
            <small>${escapeHtml(sourceLabel)}</small>
          </button>
        `;
      }).join("");
      menu.classList.add("is-open");
      input.setAttribute("aria-expanded", "true");
    }

    function formatBrowserLocationSuggestion(result) {
      const address = result.address || {};
      const primary = address.city || address.town || address.village || address.municipality || address.county || result.name;
      const region = [address.state, address.province, address.region, address.country].filter(Boolean);
      const value = [primary, ...region].filter(Boolean).join(", ") || result.display_name || "";
      return value ? { value, label: result.display_name || value, source: "openstreetmap" } : null;
    }

    function mergeLocationSuggestions(...groups) {
      const seen = new Set();
      const merged = [];
      groups.flat().forEach((suggestion) => {
        if (!suggestion || !suggestion.value) return;
        const key = suggestion.value.toLowerCase();
        if (seen.has(key)) return;
        seen.add(key);
        merged.push(suggestion);
      });
      return merged.slice(0, 8);
    }

    async function fetchBrowserLocationSuggestions(query, signal) {
      const url = new URL("https://nominatim.openstreetmap.org/search");
      url.searchParams.set("format", "jsonv2");
      url.searchParams.set("addressdetails", "1");
      url.searchParams.set("dedupe", "1");
      url.searchParams.set("limit", "8");
      url.searchParams.set("accept-language", "en");
      url.searchParams.set("q", query);

      try {
        const response = await fetch(url, { signal });
        if (!response.ok) return [];
        const payload = await response.json();
        return (Array.isArray(payload) ? payload : [])
          .map(formatBrowserLocationSuggestion)
          .filter(Boolean);
      } catch (error) {
        if (error.name === "AbortError") throw error;
        return [];
      }
    }

    function attachLocationSuggestions(input, menu) {
      let timer = null;
      let controller = null;

      input.addEventListener("input", () => {
        clearTimeout(timer);
        const query = input.value.trim();
        if (query.length < 2) {
          closeSuggestionMenu(input, menu);
          return;
        }

        timer = setTimeout(async () => {
          if (controller) controller.abort();
          controller = new AbortController();
          const url = new URL("/api/location-suggestions", window.location.origin);
          url.searchParams.set("q", query);

          try {
            const response = await fetch(url, { signal: controller.signal });
            if (!response.ok) return;
            const payload = await response.json();
            let suggestions = payload.suggestions || [];
            const onlyTyped = suggestions.length > 0 && suggestions.every((suggestion) => suggestion.source === "typed");
            if (!suggestions.length || onlyTyped) {
              const browserSuggestions = await fetchBrowserLocationSuggestions(query, controller.signal);
              suggestions = mergeLocationSuggestions(browserSuggestions, suggestions);
            }
            renderSuggestionMenu(input, menu, suggestions);
          } catch (error) {
            if (error.name !== "AbortError") closeSuggestionMenu(input, menu);
          }
        }, 220);
      });

      input.addEventListener("focus", () => {
        if (input.value.trim().length >= 2 && menu.children.length) {
          menu.classList.add("is-open");
          input.setAttribute("aria-expanded", "true");
        }
      });

      input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeSuggestionMenu(input, menu);
      });

      menu.addEventListener("click", (event) => {
        const option = event.target.closest(".suggestion-option");
        if (!option) return;
        input.value = option.dataset.value || "";
        closeSuggestionMenu(input, menu);
        input.focus();
        if (input === destinationInput) updateDestinationCopy();
      });
    }

    function updateDestinationCopy() {
      const destination = destinationInput.value.trim();
      postcardTitle.textContent = destination ? `A warmer landing in ${destination}` : "A calm first step";
      postcardCopy.textContent = destination
        ? `We will look for everyday programs that help ${destination} feel more familiar, useful, and kind.`
        : "Start with the essentials that make a new place feel navigable: food, transit, banking, phone access, health, and community.";
    }

    destinationInput.addEventListener("input", updateDestinationCopy);
    attachLocationSuggestions(originInput, originSuggestionMenu);
    attachLocationSuggestions(destinationInput, destinationSuggestionMenu);

    document.addEventListener("click", (event) => {
      if (!event.target.closest(".suggestion-wrap")) {
        closeSuggestionMenu(originInput, originSuggestionMenu);
        closeSuggestionMenu(destinationInput, destinationSuggestionMenu);
      }
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!profileFieldsValid()) {
        showFormScreen("profile");
        return;
      }
      showFormScreen("places");
      if (!originInput.reportValidity() || !destinationInput.reportValidity()) {
        return;
      }

      setLoading(true);
      categoryStack.innerHTML = "";
      const payload = {
        age: Number(ageInput.value),
        family_size: Number(familySizeInput.value),
        origin_location: originInput.value.trim(),
        destination_location: destinationInput.value.trim()
      };

      try {
        const response = await fetch("/api/recommendations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw data;
        latestResponse = data;
        renderResults(data);
        showToast("Agent recommendations are ready.");
      } catch (error) {
        renderBackendError(error);
        showToast("Backend agent did not return recommendations.");
      } finally {
        setLoading(false);
      }
    });

    function renderBackendError(error) {
      latestResponse = null;
      document.body.classList.remove("has-results");
      setDestinationBackground("");
      results.hidden = true;
      emptyState.hidden = false;
      const message = error?.message || error?.detail || "The backend agent did not return dynamic recommendations.";
      const detail = error?.detail ? `<p>${escapeHtml(error.detail)}</p>` : "";
      emptyState.innerHTML = `
        <div>
          <h2>Backend agent needs attention.</h2>
          <p>${escapeHtml(message)}</p>
          ${detail}
        </div>
      `;
    }

    function applyDestinationTheme(theme) {
      const nextTheme = theme || {};
      const root = document.documentElement;
      root.style.setProperty("--theme-primary", nextTheme.primary || "#0f766e");
      root.style.setProperty("--theme-secondary", nextTheme.secondary || "#f59e0b");
      root.style.setProperty("--theme-accent", nextTheme.accent || "#2563eb");
      root.style.setProperty("--theme-soft", nextTheme.soft || "#effaf5");
      if (nextTheme.ink) root.style.setProperty("--ink", nextTheme.ink);
    }

    function setDestinationBackground(url) {
      const cleanUrl = String(url || "").trim();
      if (!cleanUrl) {
        document.documentElement.style.setProperty("--destination-image", "none");
        document.body.classList.remove("has-destination-image");
        return;
      }

      const safeUrl = cleanUrl
        .split(String.fromCharCode(10)).join("")
        .split(String.fromCharCode(13)).join("");
      document.documentElement.style.setProperty("--destination-image", `url(${JSON.stringify(safeUrl)})`);
      document.body.classList.add("has-destination-image");
    }

    function wikipediaTitleCandidates(destination) {
      const parts = String(destination || "")
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
      const city = parts[0] || String(destination || "").trim();
      return [
        parts.slice(0, 2).join(", "),
        String(destination || "").trim(),
        city
      ].filter(Boolean).filter((value, index, list) => list.indexOf(value) === index);
    }

    async function loadDestinationBackground(destination) {
      setDestinationBackground("");

      for (const title of wikipediaTitleCandidates(destination)) {
        const slug = title.replaceAll(" ", "_");
        const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(slug)}`;
        try {
          const response = await fetch(url);
          if (!response.ok) continue;
          const payload = await response.json();
          const imageUrl = payload.originalimage?.source || payload.thumbnail?.source || "";
          if (imageUrl) {
            setDestinationBackground(imageUrl);
            return;
          }
        } catch (_) {
          return;
        }
      }
    }

    function renderResults(data) {
      applyDestinationTheme(data.destination_theme);
      loadDestinationBackground(data.profile.destination_location);
      document.body.classList.add("has-results");
      emptyState.hidden = true;
      results.hidden = false;
      welcomeTitle.textContent = data.welcome?.title || `Welcome to ${data.profile.destination_location}`;
      welcomeNotes.textContent = (data.welcome?.notes || []).join(" ");
      const citySummary = data.destination_summary || {};
      citySummaryTitle.textContent = citySummary.title || `Destination snapshot: ${data.profile.destination_location}`;
      citySummaryText.textContent = citySummary.summary || data.opening_summary || "";
      citySummaryFocus.textContent = citySummary.focus || (data.priority_categories || []).join(", ") || "Essential goods and services";
      citySummaryHousehold.textContent = citySummary.household || `Household size: ${data.profile.family_size || 1}. Prioritized for everyday essentials.`;

      const total = data.categories.reduce((sum, category) => sum + category.items.length, 0);
      queueSummary.textContent = `${total} programs across ${data.categories.length} categories. Agent mode: ${data.agent_mode.replace("_", " ")}.`;
      categoryStack.innerHTML = data.categories.map(renderCategory).join("");
      renderReview(data.compliance_review);
      document.querySelectorAll(".step").forEach((step) => step.classList.add("is-active"));
    }

    function renderCategory(category) {
      return `
        <section class="category-block" style="--accent: ${escapeHtml(category.accent)}">
          <div class="category-heading">
            <h3>${escapeHtml(category.name)}</h3>
            <span>${category.count} recommendation${category.count === 1 ? "" : "s"}</span>
          </div>
          <div class="cards">
            ${category.items.map(renderCard).join("")}
          </div>
        </section>
      `;
    }

    function renderCard(item) {
      const signup = item.signup_instructions?.length
        ? `<ol class="signup-list">${item.signup_instructions.slice(0, 3).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>`
        : `<p>Use the official page to confirm signup steps.</p>`;
      const link = item.official_url
        ? `<a href="${escapeHtml(item.official_url)}" target="_blank" rel="noreferrer">Official page</a>`
        : "Official page to verify";

      return `
        <article class="rec-card" data-card-id="${escapeHtml(item.id)}">
          <div class="rec-top">
            <div>
              <h4>${escapeHtml(item.program_name)}</h4>
              <div class="provider">${escapeHtml(item.provider)}</div>
            </div>
            <span class="confidence">${escapeHtml(item.confidence)}</span>
          </div>
          <div class="rec-body">
            <div><span class="mini-label">Why it fits</span>${escapeHtml(item.why_recommended || "A practical option for early settling needs.")}</div>
            <div><span class="mini-label">Eligibility</span>${escapeHtml(item.eligibility_notes)}</div>
            <div><span class="mini-label">Fees or checks</span>${escapeHtml(item.cost_or_fees)}</div>
            <div><span class="mini-label">Signup</span>${signup}</div>
            <div><span class="mini-label">Source</span>${link}</div>
          </div>
        </article>
      `;
    }

    function renderReview(review) {
      reviewStatus.textContent = `${review.status} - ${review.generated_at}`;
      const checks = (review.checks || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
      const redactions = (review.redactions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
      const notes = (review.agent_notes || []).length
        ? (review.agent_notes || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")
        : "<li>No human-interrupt notes were raised by the agent flow.</li>";
      const backendDetail = review.backend_error_detail
        ? `<section class="review-section"><h3>Backend detail</h3><p>${escapeHtml(review.backend_error_detail)}</p></section>`
        : "";

      reviewBody.innerHTML = `
        <section class="review-section">
          <h3>Summary</h3>
          <p>${escapeHtml(review.summary)}</p>
        </section>
        <section class="review-section">
          <h3>Checks</h3>
          <ul>${checks}</ul>
        </section>
        <section class="review-section">
          <h3>Privacy and redaction</h3>
          <ul>${redactions}</ul>
        </section>
        <section class="review-section">
          <h3>Agent notes</h3>
          <ul>${notes}</ul>
          <p>${Number(review.event_count || 0)} backend events observed.</p>
        </section>
        ${backendDetail}
      `;
    }

    function openDrawer() {
      if (!latestResponse) {
        showToast("Run a recommendation first.");
        return;
      }
      document.body.classList.add("drawer-open");
      reviewDrawer.setAttribute("aria-hidden", "false");
    }

    function closeDrawer() {
      document.body.classList.remove("drawer-open");
      reviewDrawer.setAttribute("aria-hidden", "true");
    }

    document.querySelector("#openReview").addEventListener("click", openDrawer);
    document.querySelector("#closeReview").addEventListener("click", closeDrawer);
    document.querySelector("#drawerBackdrop").addEventListener("click", closeDrawer);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeDrawer();
    });
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    import os

    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3020"))
    uvicorn.run(app, host=host, port=port, reload=False)
