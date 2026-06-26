from app.agent import RecommendationPlan, _plan_from_any


def test_recommendation_plan_accepts_numbered_next_steps_string() -> None:
    plan = RecommendationPlan.model_validate(
        {
            "opening_summary": "Local recommendations are ready.",
            "comparison_context_used": "Destination context was considered.",
            "priority_categories": ["Food and groceries", "Transit"],
            "recommendations": [],
            "next_steps": (
                "1. Visit a local branch to confirm identity requirements. "
                "2. Review newcomer resources for current signup terms."
            ),
            "disclaimer": "Verify details on official pages.",
        }
    )

    assert plan.next_steps == [
        "Visit a local branch to confirm identity requirements.",
        "Review newcomer resources for current signup terms.",
    ]


def test_plan_from_any_accepts_string_list_fields_from_llm_payload() -> None:
    plan = _plan_from_any(
        {
            "opening_summary": "A practical first pass.",
            "comparison_context_used": "Household essentials matter here.",
            "priority_categories": "1. Food and groceries\n2. Transit",
            "recommendations": [
                {
                    "program_name": "Example Rewards",
                    "provider": "Example Provider",
                    "category": "Food and groceries",
                    "why_recommended": "Useful for recurring household purchases.",
                    "signup_instructions": "1. Open the official page\n2. Create an account",
                    "confidence": "medium",
                }
            ],
            "next_steps": "- Confirm eligibility\n- Save official signup links",
        }
    )

    assert plan.priority_categories == ["Food and groceries", "Transit"]
    assert plan.next_steps == ["Confirm eligibility", "Save official signup links"]
    assert plan.recommendations[0].signup_instructions == [
        "Open the official page",
        "Create an account",
    ]
