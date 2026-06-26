# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps import App, ResumabilityConfig
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.models import Gemini
from google.adk.skills import load_skill_from_dir
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools.skill_toolset import SkillToolset
from google.adk.workflow import Workflow, node
from google.genai import types
from pydantic import BaseModel, Field, field_validator, model_validator

load_dotenv(Path(__file__).with_name(".env"))


SKILLS_DIR = Path(__file__).with_name("skills")
CUSTOMIZATION_SKILL = load_skill_from_dir(SKILLS_DIR / "customization-skill")
PROGRAM_SEARCH_SKILL = load_skill_from_dir(SKILLS_DIR / "program-search-skill")
ELIGIBILITY_SEARCH_SKILL = load_skill_from_dir(SKILLS_DIR / "eligibility-search-skill")
VERIFICATION_SKILL = load_skill_from_dir(SKILLS_DIR / "verification-skill")
SIGNUP_PROCESS_SKILL = load_skill_from_dir(SKILLS_DIR / "signup-process-skill")
RECOMMENDATION_SKILL = load_skill_from_dir(SKILLS_DIR / "recommendation-skill")

customization_skill_toolset = SkillToolset(skills=[CUSTOMIZATION_SKILL])
search_skill_toolset = SkillToolset(
    skills=[
        PROGRAM_SEARCH_SKILL,
        ELIGIBILITY_SEARCH_SKILL,
        VERIFICATION_SKILL,
        SIGNUP_PROCESS_SKILL,
    ]
)
recommendation_skill_toolset = SkillToolset(skills=[RECOMMENDATION_SKILL])
google_search_with_skills = GoogleSearchTool(bypass_multi_tools_limit=True)


MODEL = Gemini(
    model="gemini-3.1-flash-lite",
    retry_options=types.HttpRetryOptions(attempts=3),
)


class RawProfileSubmission(BaseModel):
    initial_message: str
    human_follow_up: str = ""
    current_profile_json: str = ""
    redaction_categories: list[str] = Field(default_factory=list)
    security_notes: list[str] = Field(default_factory=list)


class SecurityScreenedPayload(BaseModel):
    source: str
    sanitized_text: str
    redaction_categories: list[str] = Field(default_factory=list)
    security_notes: list[str] = Field(default_factory=list)
    prompt_injection_detected: bool = False
    injection_indicators: list[str] = Field(default_factory=list)


class SecurityReviewCase(BaseModel):
    source: str
    sanitized_text: str
    redaction_categories: list[str] = Field(default_factory=list)
    injection_indicators: list[str] = Field(default_factory=list)
    reason: str
    action: str = "route_to_human_caseworker_review"


class HouseholdMember(BaseModel):
    relationship: str = Field(
        description="Relationship to the user, such as spouse, child, parent, or self."
    )
    age: int | None = Field(
        default=None,
        description="Age in years. Use null when the age is not known.",
    )
    notes: str = ""


class NewcomerProfile(BaseModel):
    country_of_origin: str = ""
    destination: str = Field(
        default="",
        description="Destination city, region, province/state, and country when available.",
    )
    age: int | None = None
    family_size: int | None = Field(
        default=None,
        description="Total household size, including the user.",
    )
    family_members: list[HouseholdMember] = Field(default_factory=list)
    household_notes: str = ""
    constraints_or_preferences: list[str] = Field(default_factory=list)


class ProfileClarificationRequest(BaseModel):
    profile: NewcomerProfile
    missing_fields: list[str]


class MigrationComparison(BaseModel):
    origin: str
    destination: str
    comparison_summary: str
    practical_differences: list[str] = Field(default_factory=list)
    newcomer_watchouts: list[str] = Field(default_factory=list)
    context_for_future_steps: str


class CategoryNeed(BaseModel):
    category: str
    priority: str
    rationale: str
    search_focus: list[str] = Field(default_factory=list)


class SupportNeedsPlan(BaseModel):
    profile: NewcomerProfile
    comparison: MigrationComparison
    priority_categories: list[CategoryNeed]
    priority_summary: str


class CustomizationContext(BaseModel):
    profile: NewcomerProfile
    comparison: MigrationComparison
    baseline_categories: list[CategoryNeed]
    profile_summary: str


class ProgramSearchPrompt(BaseModel):
    destination: str
    search_objective: str
    priority_categories: list[CategoryNeed]
    suggested_queries: list[str]
    verification_rules: list[str]


class DiscoveredProgram(BaseModel):
    program_name: str
    provider: str
    category: str
    source_url: str = ""
    evidence_summary: str = ""
    eligibility_notes: str = ""
    signup_path: str = ""
    cost_or_fees: str = ""
    confidence: str = Field(
        default="medium",
        description="Use high, medium, or low based on source quality and local relevance."
    )

    @model_validator(mode="after")
    def _fill_evidence_summary(self) -> "DiscoveredProgram":
        if self.evidence_summary.strip():
            return self
        fallback_parts = [
            self.signup_path,
            self.eligibility_notes,
            f"Source: {self.source_url}" if self.source_url else "",
        ]
        self.evidence_summary = (
            " ".join(part.strip() for part in fallback_parts if part.strip())
            or "Evidence summary was not provided; verify details on the official provider page."
        )
        return self


class ProgramSearchResult(BaseModel):
    destination: str
    queries_used: list[str] = Field(default_factory=list)
    discovered_programs: list[DiscoveredProgram] = Field(default_factory=list)
    search_summary: str = ""
    source_notes: list[str] = Field(default_factory=list)


class ProgramResearchBrief(BaseModel):
    profile: NewcomerProfile
    comparison_summary: str
    priority_summary: str
    priority_categories: list[CategoryNeed]
    search_queries: list[str]
    search_result: ProgramSearchResult
    web_research: str


def _coerce_text_list(value: Any) -> Any:
    if value is None:
        return []
    if not isinstance(value, str):
        return value

    text = value.strip()
    if not text:
        return []

    normalized = re.sub(r"\s+(?=\d+[.)]\s+)", "\n", text)
    items: list[str] = []
    for line in normalized.splitlines():
        item = re.sub(r"^\s*(?:[-*]\s+|\d+[.)]\s+)", "", line).strip()
        if item:
            items.append(item)

    return items or [text]


class ProgramRecommendation(BaseModel):
    program_name: str
    provider: str
    category: str
    why_recommended: str
    eligibility_notes: str = ""
    signup_instructions: list[str] = Field(default_factory=list)
    official_url: str = ""
    cost_or_fees: str = ""
    confidence: str = Field(
        description="Use high, medium, or low based on how directly the web research supports it."
    )
    caution_notes: str = ""

    @field_validator("signup_instructions", mode="before")
    @classmethod
    def _coerce_signup_instructions(cls, value: Any) -> Any:
        return _coerce_text_list(value)


class RecommendationPlan(BaseModel):
    opening_summary: str
    comparison_context_used: str
    priority_categories: list[str] = Field(default_factory=list)
    recommendations: list[ProgramRecommendation] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    disclaimer: str = ""

    @field_validator("priority_categories", "next_steps", mode="before")
    @classmethod
    def _coerce_string_lists(cls, value: Any) -> Any:
        return _coerce_text_list(value)


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, types.Content):
        return " ".join(part.text for part in content.parts or [] if part.text).strip()
    if hasattr(content, "parts"):
        return " ".join(part.text for part in content.parts or [] if part.text).strip()
    return str(content).strip()


PII_REDACTION_RULES: tuple[tuple[str, str], ...] = (
    (
        "email_address",
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    ),
    (
        "immigration_id",
        r"\b(?:UCI|I-94|A[- ]?number|alien registration|immigration id|PR card|green card)\s*(?:number|no\.?|#|is|:)?\s*[A-Z0-9][A-Z0-9 -]{4,24}\b",
    ),
    (
        "passport_number",
        r"\bpassport\s*(?:number|no\.?|#|is|:)?\s*[A-Z0-9][A-Z0-9 -]{5,24}\b",
    ),
    (
        "sin_ssn_number",
        r"\b(?:SIN|SSN|social insurance number|social security number)\s*(?:number|no\.?|#|is|:)?\s*\d{3}[- ]?\d{2,3}[- ]?\d{3,4}\b",
    ),
    (
        "sin_ssn_number",
        r"\b\d{3}-\d{2}-\d{4}\b",
    ),
    (
        "bank_account_details",
        r"\b(?:routing number|transit number|institution number|bank account|account number|checking account|chequing account|savings account)\s*(?:number|no\.?|#|is|:)?\s*[A-Z0-9][A-Z0-9 -]{4,30}\b",
    ),
    (
        "bank_account_details",
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
    ),
    (
        "phone_number",
        r"\b(?:phone|mobile|cell|telephone|tel|call me at)\s*(?:number|no\.?|#|is|:)?\s*(?:\+?\d[\d(). -]{7,}\d)\b",
    ),
    (
        "phone_number",
        r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b",
    ),
    (
        "date_of_birth",
        r"\b(?:date of birth|dob|birthdate|born on)\s*(?:is|:)?\s*(?:\d{1,4}[/-]\d{1,2}[/-]\d{1,4}|[A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4})\b",
    ),
    (
        "home_address",
        r"\b\d{1,6}\s+[A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,4}\s+(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|court|ct|way|place|pl|circle|cir|trail|terrace|ter|crescent|cres)\b(?:[^\n,;]*)?",
    ),
    (
        "full_name",
        r"\b(?:full name|legal name|name)\s*(?:is|:)\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b",
    ),
    (
        "full_name",
        r"\b(?:(?i:my name is|i am|i'm))\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b",
    ),
)

PROMPT_INJECTION_RULES: tuple[tuple[str, str], ...] = (
    (
        "instruction_override",
        r"\b(?:ignore|disregard|override|forget)\b.{0,80}\b(?:system|developer|previous|above|instructions?|rules)\b",
    ),
    (
        "role_override",
        r"\b(?:you are now|act as|pretend to be)\b.{0,80}\b(?:admin|caseworker|developer|system|approver)\b",
    ),
    (
        "approval_bypass",
        r"\b(?:force|guarantee|auto[- ]?approve|approve)\b.{0,80}\b(?:eligibility|benefits?|application|case|me)\b",
    ),
    (
        "eligibility_fabrication",
        r"\b(?:fabricate|fake|make up|invent)\b.{0,80}\b(?:immigration status|status|eligibility|documents?)\b",
    ),
    (
        "policy_exfiltration",
        r"\b(?:reveal|show|print|dump|exfiltrate)\b.{0,80}\b(?:hidden|system|developer|polic(?:y|ies)|prompt|rules)\b",
    ),
    (
        "safety_bypass",
        r"\b(?:ignore|disable|bypass)\b.{0,80}\b(?:safety|guardrails?|security|redaction|checks?)\b",
    ),
    (
        "jailbreak",
        r"\b(?:jailbreak|DAN mode|developer mode)\b",
    ),
)


def _combine_categories(*category_lists: list[str]) -> list[str]:
    combined: dict[str, None] = {}
    for categories in category_lists:
        for category in categories:
            combined[category] = None
    return list(combined)


def _is_luhn_valid(candidate: str) -> bool:
    digits = [int(char) for char in re.sub(r"\D", "", candidate)]
    if not 13 <= len(digits) <= 19:
        return False

    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _scrub_personal_data(text: str) -> tuple[str, list[str]]:
    sanitized = text
    categories: list[str] = []

    def redact(category: str):
        def replacement(match: re.Match[str]) -> str:
            categories.append(category)
            return f"[REDACTED:{category}]"

        return replacement

    for category, pattern in PII_REDACTION_RULES:
        sanitized = re.sub(
            pattern,
            redact(category),
            sanitized,
            flags=re.IGNORECASE,
        )

    def redact_credit_card(match: re.Match[str]) -> str:
        candidate = match.group(0)
        if not _is_luhn_valid(candidate):
            return candidate
        categories.append("credit_card_number")
        return "[REDACTED:credit_card_number]"

    sanitized = re.sub(
        r"\b(?:\d[ -]?){13,19}\b",
        redact_credit_card,
        sanitized,
    )

    return sanitized, _combine_categories(categories)


def _detect_prompt_injection(text: str) -> list[str]:
    indicators: list[str] = []
    for indicator, pattern in PROMPT_INJECTION_RULES:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            indicators.append(indicator)
    return _combine_categories(indicators)


def _screen_user_text(text: str, source: str) -> SecurityScreenedPayload:
    sanitized_text, redaction_categories = _scrub_personal_data(text)
    injection_indicators = _detect_prompt_injection(text)
    security_notes: list[str] = []
    if redaction_categories:
        security_notes.append(
            "Sensitive fields were redacted before model or review processing."
        )
    if injection_indicators:
        security_notes.append(
            "Prompt-injection indicators were detected and routed to human review."
        )

    return SecurityScreenedPayload(
        source=source,
        sanitized_text=sanitized_text,
        redaction_categories=redaction_categories,
        security_notes=security_notes,
        prompt_injection_detected=bool(injection_indicators),
        injection_indicators=injection_indicators,
    )


def _security_review_case(screening: SecurityScreenedPayload) -> SecurityReviewCase:
    return SecurityReviewCase(
        source=screening.source,
        sanitized_text=screening.sanitized_text,
        redaction_categories=screening.redaction_categories,
        injection_indicators=screening.injection_indicators,
        reason=(
            "Potential prompt-injection or policy-bypass instructions were detected. "
            "The raw payload was not passed to downstream LLM nodes."
        ),
    )


def _security_state_delta(
    ctx: Context, screening: SecurityScreenedPayload, *, review_required: bool
) -> dict[str, Any]:
    cumulative_redactions = _combine_categories(
        list(ctx.state.get("redaction_categories") or []),
        screening.redaction_categories,
    )
    checkpoint = {
        "source": screening.source,
        "redaction_categories": screening.redaction_categories,
        "prompt_injection_detected": screening.prompt_injection_detected,
        "injection_indicators": screening.injection_indicators,
        "review_required": review_required,
    }
    return {
        "redaction_categories": cumulative_redactions,
        "last_security_checkpoint": checkpoint,
        "security_review_required": review_required,
    }


def _screened_payload_from_any(value: Any, source: str) -> SecurityScreenedPayload:
    if isinstance(value, SecurityScreenedPayload):
        return value
    if isinstance(value, dict) and "sanitized_text" in value:
        return SecurityScreenedPayload.model_validate(value)
    return _screen_user_text(_content_to_text(value), source)


def _profile_from_any(value: NewcomerProfile | dict[str, Any]) -> NewcomerProfile:
    if isinstance(value, NewcomerProfile):
        return value
    return NewcomerProfile.model_validate(value)


def _comparison_from_any(
    value: MigrationComparison | dict[str, Any],
) -> MigrationComparison:
    if isinstance(value, MigrationComparison):
        return value
    return MigrationComparison.model_validate(value)


def _plan_from_any(value: RecommendationPlan | dict[str, Any]) -> RecommendationPlan:
    if isinstance(value, RecommendationPlan):
        return value
    return RecommendationPlan.model_validate(value)


def _fallback_support_needs_plan(
    fallback_context: CustomizationContext | dict[str, Any],
) -> SupportNeedsPlan:
    context = (
        fallback_context
        if isinstance(fallback_context, CustomizationContext)
        else CustomizationContext.model_validate(fallback_context)
    )
    priority_categories = context.baseline_categories or _build_priority_categories(
        context.profile
    )
    category_names = ", ".join(
        category.category for category in priority_categories
    ) or "essential newcomer services"
    return SupportNeedsPlan(
        profile=context.profile,
        comparison=context.comparison,
        priority_categories=priority_categories,
        priority_summary=(
            "The customization model did not return a structured plan, so the "
            f"workflow is using conservative baseline essentials: {category_names}."
        ),
    )


def _support_needs_plan_from_any(
    value: SupportNeedsPlan | dict[str, Any] | None,
    *,
    fallback_context: CustomizationContext | dict[str, Any] | None = None,
) -> SupportNeedsPlan:
    if isinstance(value, SupportNeedsPlan):
        return value
    if isinstance(value, dict):
        return SupportNeedsPlan.model_validate(value)
    if value is None and fallback_context is not None:
        return _fallback_support_needs_plan(fallback_context)
    raise RuntimeError(
        "customize_essentials returned no support_needs_plan and no "
        "customization_context was available for a deterministic fallback."
    )


def _looks_like_complete_profile(text: str) -> bool:
    lowered = text.lower()
    has_origin = any(
        marker in lowered
        for marker in (
            "country of origin",
            "origin location",
            "origin:",
            "from ",
            "coming from",
            "born in",
        )
    )
    has_destination = any(
        marker in lowered
        for marker in (
            "destination",
            "destination location",
            "moving to",
            "settling in",
            "relocating to",
            "to ",
        )
    )
    has_age = any(marker in lowered for marker in ("age", "years old", "yo"))
    has_family = any(
        marker in lowered
        for marker in (
            "family",
            "family size",
            "household size",
            "household",
            "spouse",
            "partner",
            "child",
            "children",
            "kids",
            "alone",
            "single",
        )
    )
    return has_origin and has_destination and has_age and has_family


def _profile_missing_fields(profile: NewcomerProfile) -> list[str]:
    missing: list[str] = []
    if not profile.country_of_origin.strip():
        missing.append("country of origin")
    if not profile.destination.strip():
        missing.append("destination")
    if profile.age is None or profile.age <= 0:
        missing.append("age")
    if profile.family_size is None or profile.family_size <= 0:
        missing.append("family size")
    return missing


def _member_is_child(member: HouseholdMember) -> bool:
    relationship = member.relationship.lower()
    return "child" in relationship or "kid" in relationship or (
        member.age is not None and member.age < 18
    )


def _build_priority_categories(profile: NewcomerProfile) -> list[CategoryNeed]:
    categories = [
        CategoryNeed(
            category="Food and groceries",
            priority="high",
            rationale="Groceries are an immediate recurring cost, and local chains often have loyalty pricing, points, coupons, or newcomer-friendly apps.",
            search_focus=[
                "supermarket loyalty",
                "major local grocery chains loyalty",
                "pharmacy grocery points",
                "coupon app",
            ],
        ),
        CategoryNeed(
            category="Transit and mobility",
            priority="high",
            rationale="A newcomer usually needs reliable local transportation before routines are settled.",
            search_focus=[
                "transit fare discount",
                "reloadable fare card rewards",
                "bike share or car share membership",
            ],
        ),
        CategoryNeed(
            category="Banking",
            priority="high",
            rationale="A local bank account can unlock payroll, rent payments, debit rewards, and newcomer banking offers.",
            search_focus=[
                "newcomer bank account bonus",
                "debit rewards",
                "no monthly fee account",
            ],
        ),
        CategoryNeed(
            category="Healthcare and pharmacy",
            priority="medium",
            rationale="Healthcare coverage and pharmacy access differ by destination, so the search should include both commercial pharmacy rewards and official government healthcare benefit programs without giving medical advice.",
            search_focus=[
                "commercial pharmacy rewards",
                "prescription savings card",
                "government healthcare benefits",
                "public prescription drug benefit",
            ],
        ),
        CategoryNeed(
            category="Housing and utilities",
            priority="medium",
            rationale="Housing does not always have classic loyalty programs, so the search should include rent rewards, utility discounts, and local housing benefit programs.",
            search_focus=[
                "rent rewards",
                "utility discount program",
                "tenant benefit program",
            ],
        ),
        CategoryNeed(
            category="Cellular and telecommunications",
            priority="medium",
            rationale="Mobile phone and internet access are recurring setup costs for newcomers, and local carriers or public programs may offer prepaid, multi-line, newcomer, low-income, or bundled discounts.",
            search_focus=[
                "mobile carrier rewards",
                "prepaid phone plan discount",
                "internet affordability program",
                "telecommunications bundle reward",
            ],
        ),
    ]

    age = profile.age or 0
    if age >= 18:
        categories.append(
            CategoryNeed(
                category="Credit cards and credit building",
                priority="medium",
                rationale="Adult newcomers may need to build local credit history, but offers should be screened for fees, interest, credit checks, and eligibility.",
                search_focus=[
                    "newcomer credit card rewards",
                    "secured credit card",
                    "no annual fee rewards card",
                ],
            )
        )

    family_size = profile.family_size or 1
    if family_size > 1:
        categories.append(
            CategoryNeed(
                category="Shared household essentials",
                priority="high" if family_size >= 4 else "medium",
                rationale=(
                    f"A household of {family_size} people may benefit from rewards "
                    "and discounts that reduce recurring shared costs without assuming "
                    "the household includes children."
                ),
                search_focus=[
                    "family grocery rewards",
                    "household essentials discount",
                    "multi line mobile plan discount",
                    "community recreation family membership",
                ],
            )
        )

    has_children = any(_member_is_child(member) for member in profile.family_members)
    if has_children:
        categories.append(
            CategoryNeed(
                category="Family and child essentials",
                priority="high",
                rationale="Households with children often benefit from family transit fares, grocery points, school supplies discounts, and recreation memberships.",
                search_focus=[
                    "family transit pass",
                    "kids recreation discount",
                    "school supplies rewards",
                ],
            )
        )

    if profile.family_size and profile.family_size >= 4:
        categories.append(
            CategoryNeed(
                category="Bulk household purchasing",
                priority="medium",
                rationale="Larger households can benefit from warehouse clubs, bulk grocery rewards, and recurring delivery discounts.",
                search_focus=[
                    "warehouse club membership",
                    "bulk grocery rewards",
                    "household delivery subscription discount",
                ],
            )
        )

    if age >= 60:
        categories.append(
            CategoryNeed(
                category="Senior discounts",
                priority="high",
                rationale="Older newcomers may qualify for age-based transit, pharmacy, grocery, banking, and community discounts.",
                search_focus=[
                    "senior transit discount",
                    "senior pharmacy discount",
                    "senior banking offer",
                ],
            )
        )

    return categories


def _profile_summary(profile: NewcomerProfile) -> str:
    age = "unknown age" if profile.age is None else f"age {profile.age}"
    family = (
        "unknown household size"
        if profile.family_size is None
        else f"household of {profile.family_size}"
    )
    return (
        f"Origin: {profile.country_of_origin or 'unknown'}; "
        f"Destination: {profile.destination or 'unknown'}; {age}; {family}."
    )


def _visible_message_event(message: str) -> Event:
    return Event(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=message)],
        )
    )


@node(name="security_checkpoint")
def security_checkpoint(ctx: Context, node_input: types.Content) -> Event:
    screening = _screen_user_text(_content_to_text(node_input), "initial_user_payload")
    if screening.prompt_injection_detected:
        return Event(
            output=_security_review_case(screening),
            route="security_review",
            state=_security_state_delta(ctx, screening, review_required=True),
        )

    return Event(
        output=screening,
        route="clean",
        state=_security_state_delta(ctx, screening, review_required=False),
    )


@node(name="request_security_review", rerun_on_resume=True)
async def request_security_review(
    ctx: Context, node_input: SecurityReviewCase | dict[str, Any]
) -> AsyncGenerator[RequestInput | Event, None]:
    review_case = (
        node_input
        if isinstance(node_input, SecurityReviewCase)
        else SecurityReviewCase.model_validate(node_input)
    )
    interrupt_id = f"security_review_{review_case.source}"
    message = (
        "Security checkpoint routed this request to human caseworker/admin "
        "review before any LLM reviewer, recommendation, document-analysis, "
        "or benefits-matching step.\n\n"
        f"Reason: {review_case.reason}\n"
        "Redacted categories: "
        f"{', '.join(review_case.redaction_categories) or 'none'}\n"
        "Injection indicators: "
        f"{', '.join(review_case.injection_indicators) or 'none'}\n\n"
        "Sanitized payload for review:\n"
        f"{review_case.sanitized_text}\n\n"
        "Review this case outside the automated recommendation flow."
    )

    if interrupt_id not in (ctx.resume_inputs or {}):
        yield _visible_message_event(message)
        yield RequestInput(
            interrupt_id=interrupt_id,
            message=message,
            payload=review_case.model_dump(),
            response_schema=str,
        )
        return

    answer = "Security review note recorded. Automated recommendation flow remains paused."
    yield Event(
        output=answer,
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=answer)],
        ),
    )


@node(name="collect_profile_submission", rerun_on_resume=True)
async def collect_profile_submission(
    ctx: Context, node_input: SecurityScreenedPayload | dict[str, Any] | types.Content
) -> AsyncGenerator[RequestInput | Event, None]:
    initial_screening = _screened_payload_from_any(node_input, "initial_user_payload")
    if initial_screening.prompt_injection_detected:
        yield Event(
            output=_security_review_case(initial_screening),
            route="security_review",
            state=_security_state_delta(ctx, initial_screening, review_required=True),
        )
        return

    initial_message = initial_screening.sanitized_text
    interrupt_id = "newcomer_profile_details"

    if not _looks_like_complete_profile(initial_message) and interrupt_id not in (
        ctx.resume_inputs or {}
    ):
        message = (
            "Please share your origin location, destination location, age, "
            "and family or household size. A compact format is fine, for "
            "example: origin, destination, my age, household size."
        )
        yield _visible_message_event(message)
        yield RequestInput(
            interrupt_id=interrupt_id,
            message=message,
            response_schema=str,
        )
        return

    follow_up_screening = _screen_user_text(
        str((ctx.resume_inputs or {}).get(interrupt_id, "")),
        "profile_follow_up",
    )
    if follow_up_screening.prompt_injection_detected:
        yield Event(
            output=_security_review_case(follow_up_screening),
            route="security_review",
            state=_security_state_delta(ctx, follow_up_screening, review_required=True),
        )
        return

    redaction_categories = _combine_categories(
        initial_screening.redaction_categories,
        follow_up_screening.redaction_categories,
    )
    security_notes = [
        *initial_screening.security_notes,
        *follow_up_screening.security_notes,
    ]
    yield Event(
        output=RawProfileSubmission(
            initial_message=initial_message,
            human_follow_up=follow_up_screening.sanitized_text,
            redaction_categories=redaction_categories,
            security_notes=security_notes,
        ),
        route="clean",
        state=_security_state_delta(ctx, follow_up_screening, review_required=False),
    )


extract_profile = LlmAgent(
    name="extract_profile",
    model=MODEL,
    input_schema=RawProfileSubmission,
    output_schema=NewcomerProfile,
    output_key="newcomer_profile",
    instruction=(
        "Extract the newcomer profile from the initial message and any human "
        "follow-up. Normalize the destination to include city/region/country "
        "when present. Include the user as a household member when possible. "
        "Family member ages are optional; when only household size is provided, "
        "set family_size and do not ask for additional ages. "
        "Use null for unknown numeric ages and empty strings for unknown text. "
        "Return only data matching the schema."
    ),
)


@node(name="validate_profile")
def validate_profile(node_input: NewcomerProfile | dict[str, Any]) -> Event:
    profile = _profile_from_any(node_input)
    missing_fields = _profile_missing_fields(profile)
    if missing_fields:
        return Event(
            output=ProfileClarificationRequest(
                profile=profile, missing_fields=missing_fields
            ),
            route="needs_clarification",
        )

    return Event(
        output=profile,
        route="complete",
        state={"newcomer_profile": profile.model_dump()},
    )


@node(name="request_profile_clarification", rerun_on_resume=True)
async def request_profile_clarification(
    ctx: Context, node_input: ProfileClarificationRequest | dict[str, Any]
) -> AsyncGenerator[RequestInput | Event, None]:
    request = (
        node_input
        if isinstance(node_input, ProfileClarificationRequest)
        else ProfileClarificationRequest.model_validate(node_input)
    )
    interrupt_id = "newcomer_profile_clarification"

    if interrupt_id not in (ctx.resume_inputs or {}):
        current_profile_json = _scrub_personal_data(
            request.profile.model_dump_json(indent=2)
        )[0]
        message = (
            "I need a little more detail before searching for local "
            "programs. Missing: "
            f"{', '.join(request.missing_fields)}.\n\n"
            "Current profile:\n"
            f"{current_profile_json}\n\n"
            "Please provide the missing details."
        )
        yield _visible_message_event(message)
        yield RequestInput(
            interrupt_id=interrupt_id,
            message=message,
            response_schema=str,
        )
        return

    follow_up_screening = _screen_user_text(
        str(ctx.resume_inputs[interrupt_id]),
        "profile_clarification",
    )
    if follow_up_screening.prompt_injection_detected:
        yield Event(
            output=_security_review_case(follow_up_screening),
            route="security_review",
            state=_security_state_delta(ctx, follow_up_screening, review_required=True),
        )
        return

    current_profile_json, profile_redactions = _scrub_personal_data(
        request.profile.model_dump_json()
    )
    redaction_categories = _combine_categories(
        follow_up_screening.redaction_categories,
        profile_redactions,
    )
    yield Event(
        output=RawProfileSubmission(
            initial_message="",
            human_follow_up=follow_up_screening.sanitized_text,
            current_profile_json=current_profile_json,
            redaction_categories=redaction_categories,
            security_notes=follow_up_screening.security_notes,
        ),
        route="clean",
        state=_security_state_delta(ctx, follow_up_screening, review_required=False),
    )


extract_clarified_profile = LlmAgent(
    name="extract_clarified_profile",
    model=MODEL,
    input_schema=RawProfileSubmission,
    output_schema=NewcomerProfile,
    output_key="newcomer_profile",
    instruction=(
        "Merge the current profile JSON with the user's clarification. Keep "
        "previously known values unless the clarification replaces them. "
        "Return a complete NewcomerProfile matching the schema."
    ),
)


compare_origin_destination = LlmAgent(
    name="compare_origin_destination",
    model=MODEL,
    input_schema=NewcomerProfile,
    output_schema=MigrationComparison,
    output_key="migration_comparison",
    instruction=(
        "Compare the user's country of origin with their destination for the "
        "purpose of finding loyalty, rewards, discount, and essential-service "
        "programs. Keep the comparison concise and practical. Focus on food "
        "retail norms, healthcare/pharmacy access, banking and credit history, "
        "housing or utilities, cellular and internet access, transit, "
        "language/currency/documentation, and "
        "any differences that should guide later search and recommendations. "
        "Do not provide legal, medical, or financial advice. Return only data "
        "matching the schema."
    ),
)


@node(name="build_customization_context")
def build_customization_context(
    ctx: Context, node_input: MigrationComparison | dict[str, Any]
) -> Event:
    comparison = _comparison_from_any(node_input)
    profile = NewcomerProfile.model_validate(ctx.state["newcomer_profile"])
    context = CustomizationContext(
        profile=profile,
        comparison=comparison,
        baseline_categories=_build_priority_categories(profile),
        profile_summary=_profile_summary(profile),
    )
    return Event(
        output=context,
        state={
            "migration_comparison": comparison.model_dump(),
            "customization_context": context.model_dump(),
        },
    )


customize_essentials = LlmAgent(
    name="customize_essentials",
    model=MODEL,
    input_schema=CustomizationContext,
    output_schema=SupportNeedsPlan,
    output_key="support_needs_plan",
    tools=[customization_skill_toolset],
    instruction=(
        "You are the customization node in a graph workflow. First load the "
        "`customization-skill` with the skill tools, then follow it to decide "
        "which essential categories deserve local loyalty or rewards search. "
        "Use the baseline categories as candidates, but revise priorities, "
        "add demographic essentials, or remove weak categories when the skill "
        "instructions and user profile support it. Return only data matching "
        "the requested schema."
    ),
)


@node(name="build_program_search_prompt")
def build_program_search_prompt(
    ctx: Context, node_input: SupportNeedsPlan | dict[str, Any] | None = None
) -> Event:
    plan = _support_needs_plan_from_any(
        node_input,
        fallback_context=ctx.state.get("customization_context"),
    )
    destination = plan.profile.destination
    suggested_queries: list[str] = []
    for category in plan.priority_categories:
        for focus in category.search_focus[:2]:
            suggested_queries.append(
                f"{destination} {focus} loyalty rewards signup official"
            )

    suggested_queries.extend(
        [
            f"{destination} newcomer banking rewards account bonus official",
            f"{destination} transit fare discount pass official",
            f"{destination} grocery loyalty program signup official",
            f"{destination} major grocery chains loyalty rewards official",
            f"{destination} supermarket rewards digital coupons official",
            f"{destination} commercial pharmacy rewards program official",
            f"{destination} government healthcare benefits newcomer official",
            f"{destination} public prescription drug benefit eligibility official",
            f"{destination} mobile phone plan rewards discount official",
            f"{destination} internet affordability program telecom discount official",
            f"{destination} telecom loyalty rewards signup official",
        ]
    )

    prompt = ProgramSearchPrompt(
        destination=destination,
        search_objective=(
            "Find current local loyalty, rewards, discount, and member programs "
            "for essential newcomer needs. Prefer official pages and include "
            "eligibility summaries, signup instructions, and links. For every "
            "priority category, gather enough candidates for the recommendation "
            "node to select the top three loyalty or rewards programs when "
            "evidence supports them. For grocery needs, identify named supermarket "
            "or grocery chains that actually serve the destination and verify "
            "their official loyalty, member pricing, rewards, or digital coupon "
            "programs. For cellular and telecommunications needs, include mobile "
            "carrier rewards, prepaid plan discounts, internet affordability "
            "programs, multi-line offers, and bundle rewards only when they are "
            "verified for the destination or service area. For healthcare and "
            "pharmacy needs, search both commercial pharmacy loyalty, rewards, "
            "and prescription savings programs, and official government "
            "healthcare, prescription, or coverage benefit programs."
        ),
        priority_categories=plan.priority_categories,
        suggested_queries=list(dict.fromkeys(suggested_queries)),
        verification_rules=[
            "Prefer official provider, government health agency, government benefits portal, transit agency, bank, pharmacy, or retailer pages.",
            "For grocery results, prefer named local grocery chains with official loyalty or coupon pages over generic grocery advice.",
            "For healthcare and pharmacy results, clearly distinguish commercial pharmacy programs from government healthcare or prescription benefits.",
            "Keep third-party aggregator results only when they point to an official signup path.",
            "Flag eligibility limits, fees, credit checks, geographic limits, and uncertain evidence.",
            "Do not invent program names, URLs, or signup steps.",
        ],
    )
    return Event(
        output=prompt,
        state={
            "support_needs_plan": plan.model_dump(),
            "priority_needs_summary": plan.priority_summary,
            "program_search_prompt": prompt.model_dump(),
            "program_search_queries": prompt.suggested_queries,
        },
    )


discover_local_programs = LlmAgent(
    name="discover_local_programs",
    model=MODEL,
    input_schema=ProgramSearchPrompt,
    output_schema=ProgramSearchResult,
    output_key="program_search_result",
    tools=[search_skill_toolset, google_search_with_skills],
    instruction=(
        "You are the search node in a graph workflow. First load these four "
        "skills with the skill tools: `program-search-skill`, "
        "`eligibility-search-skill`, `verification-skill`, and "
        "`signup-process-skill`. Use Google Search to find current local "
        "loyalty, rewards, discount, member, and essential-service programs. "
        "Search across the supplied destination, priority categories, and "
        "queries. For each priority category, collect enough verified candidates "
        "for the recommendation node to choose the top three loyalty or rewards "
        "programs when evidence supports them. For grocery and household "
        "essentials, first identify named grocery chains serving the destination, "
            "then search their official loyalty, rewards, member pricing, or digital "
            "coupon pages. For cellular and telecommunications essentials, search "
            "local mobile carriers, internet providers, public affordability "
            "programs, multi-line offers, prepaid discounts, and bundle rewards. "
            "For healthcare and pharmacy essentials, search both commercial "
            "pharmacy loyalty/rewards programs and official government "
            "healthcare or prescription benefit pages, clearly labeling which "
            "type each candidate is. "
            "Prefer official signup pages. Capture program name, "
            "provider, category, source URL, evidence_summary, eligibility_notes, "
        "cost_or_fees, signup_path, and confidence for every discovered program. "
        "Return only data matching the requested schema. Do not rely on memory."
    ),
)


@node(name="package_program_research")
def package_program_research(
    ctx: Context, node_input: ProgramSearchResult | dict[str, Any]
) -> Event:
    profile = NewcomerProfile.model_validate(ctx.state["newcomer_profile"])
    comparison = MigrationComparison.model_validate(ctx.state["migration_comparison"])
    needs_plan = SupportNeedsPlan.model_validate(ctx.state["support_needs_plan"])
    search_prompt = ProgramSearchPrompt.model_validate(ctx.state["program_search_prompt"])
    search_result = (
        node_input
        if isinstance(node_input, ProgramSearchResult)
        else ProgramSearchResult.model_validate(node_input)
    )

    brief = ProgramResearchBrief(
        profile=profile,
        comparison_summary=comparison.context_for_future_steps
        or comparison.comparison_summary,
        priority_summary=needs_plan.priority_summary,
        priority_categories=needs_plan.priority_categories,
        search_queries=search_prompt.suggested_queries,
        search_result=search_result,
        web_research=search_result.search_summary,
    )
    return Event(
        output=brief,
        state={
            "program_research_brief": brief.model_dump(),
            "web_research_summary": search_result.search_summary[:4000],
        },
    )


recommend_programs = LlmAgent(
    name="recommend_programs",
    model=MODEL,
    input_schema=ProgramResearchBrief,
    output_schema=RecommendationPlan,
    output_key="recommendation_plan",
    tools=[recommendation_skill_toolset],
    instruction=(
        "You are the recommendation node in a graph workflow. First load the "
        "`recommendation-skill` with the skill tools, then use the profile, "
        "migration comparison, priority needs, and discovered program evidence "
        "to recommend the best local loyalty, rewards, discount, or member "
        "programs. For every essential goods or service category in the priority "
        "needs, determine the top three loyalty or rewards programs when enough "
        "verified evidence supports them. If fewer than three credible programs "
        "exist for a category, return only the credible programs and preserve "
        "the category. "
        "For cellular and telecommunications categories, consider verified "
        "mobile, prepaid, internet affordability, multi-line, and bundle reward "
        "programs when applicable to the destination or service area. "
        "For healthcare and pharmacy categories, consider both verified "
        "commercial pharmacy rewards or prescription savings programs and "
        "official government healthcare benefits, while avoiding medical advice. "
        "Use official URLs and signup steps from the search result. Do not "
        "invent programs, URLs, fees, or eligibility. Return only data matching "
        "the requested schema."
    ),
)


@node(name="final_response")
def final_response(ctx: Context, node_input: RecommendationPlan | dict[str, Any]) -> Event:
    plan = _plan_from_any(node_input)
    lines = [
        plan.opening_summary,
        "",
        "## Context used",
        plan.comparison_context_used,
        "",
        "## Priority areas",
        ", ".join(plan.priority_categories) if plan.priority_categories else "None listed.",
        "",
        "## Recommended programs",
    ]

    if not plan.recommendations:
        lines.append(
            "I could not find enough well-supported local programs to recommend. "
            "Try again with a more specific destination, such as a city and state/province."
        )
    else:
        for index, recommendation in enumerate(plan.recommendations, start=1):
            lines.extend(
                [
                    "",
                    f"{index}. **{recommendation.program_name}** - {recommendation.provider}",
                    f"   - Category: {recommendation.category}",
                    f"   - Why it fits: {recommendation.why_recommended}",
                    f"   - Eligibility: {recommendation.eligibility_notes or 'Verify on the official page.'}",
                    f"   - Fees/checks: {recommendation.cost_or_fees or 'Verify before signing up.'}",
                    "   - Signup:",
                ]
            )
            if recommendation.signup_instructions:
                lines.extend(
                    f"     {step_number}. {step}"
                    for step_number, step in enumerate(
                        recommendation.signup_instructions, start=1
                    )
                )
            else:
                lines.append("     1. Use the official page to confirm signup steps.")
            lines.extend(
                [
                    f"   - Link: {recommendation.official_url or 'No official URL found in research.'}",
                    f"   - Confidence: {recommendation.confidence}",
                ]
            )
            if recommendation.caution_notes:
                lines.append(f"   - Note: {recommendation.caution_notes}")

    if plan.next_steps:
        lines.extend(["", "## Next steps"])
        lines.extend(f"- {step}" for step in plan.next_steps)

    if plan.disclaimer:
        lines.extend(["", plan.disclaimer])

    redaction_categories = list(ctx.state.get("redaction_categories") or [])
    if redaction_categories:
        lines.extend(
            [
                "",
                "Sensitive fields protected: "
                f"{', '.join(redaction_categories)} were redacted before model processing.",
            ]
        )

    answer = "\n".join(lines).strip()
    return Event(
        output=answer,
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=answer)],
        ),
    )


root_agent = Workflow(
    name="root_agent",
    edges=[
        ("START", security_checkpoint),
        (
            security_checkpoint,
            {
                "clean": collect_profile_submission,
                "security_review": request_security_review,
            },
        ),
        (
            collect_profile_submission,
            {
                "clean": extract_profile,
                "security_review": request_security_review,
            },
        ),
        (extract_profile, validate_profile),
        (
            validate_profile,
            {
                "complete": compare_origin_destination,
                "needs_clarification": request_profile_clarification,
            },
        ),
        (
            request_profile_clarification,
            {
                "clean": extract_clarified_profile,
                "security_review": request_security_review,
            },
        ),
        (extract_clarified_profile, compare_origin_destination),
        (compare_origin_destination, build_customization_context),
        (build_customization_context, customize_essentials),
        (customize_essentials, build_program_search_prompt),
        (build_program_search_prompt, discover_local_programs),
        (discover_local_programs, package_program_research),
        (package_program_research, recommend_programs),
        (recommend_programs, final_response),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
    resumability_config=ResumabilityConfig(is_resumable=True),
)
