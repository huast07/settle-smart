import pytest

from app.agent import (
    CategoryNeed,
    CustomizationContext,
    MigrationComparison,
    NewcomerProfile,
    SupportNeedsPlan,
    _support_needs_plan_from_any,
)


def _customization_context() -> CustomizationContext:
    profile = NewcomerProfile(
        country_of_origin="Toronto, Ontario, Canada",
        destination="San Francisco, California, United States",
        age=34,
        family_size=4,
    )
    comparison = MigrationComparison(
        origin="Toronto, Ontario, Canada",
        destination="San Francisco, California, United States",
        comparison_summary="Transit, grocery, banking, and pharmacy setup differ.",
        practical_differences=["Grocery loyalty programs are retailer-specific."],
        newcomer_watchouts=["Verify fees and service area before enrollment."],
        context_for_future_steps=(
            "Prioritize food, transit, pharmacy, banking, and household essentials."
        ),
    )
    baseline_categories = [
        CategoryNeed(
            category="Food and groceries",
            priority="high",
            rationale="A larger household benefits from grocery loyalty savings.",
            search_focus=["major grocery chains", "digital coupons"],
        ),
        CategoryNeed(
            category="Shared household essentials",
            priority="high",
            rationale="Family size increases the relevance of recurring essentials.",
            search_focus=["bulk household purchasing", "family essentials"],
        ),
    ]
    return CustomizationContext(
        profile=profile,
        comparison=comparison,
        baseline_categories=baseline_categories,
        profile_summary="Adult newcomer household of 4 moving to San Francisco.",
    )


def test_none_support_needs_plan_falls_back_to_customization_context() -> None:
    plan = _support_needs_plan_from_any(
        None,
        fallback_context=_customization_context().model_dump(),
    )

    assert isinstance(plan, SupportNeedsPlan)
    assert plan.profile.destination == "San Francisco, California, United States"
    assert plan.comparison.origin == "Toronto, Ontario, Canada"
    assert [category.category for category in plan.priority_categories] == [
        "Food and groceries",
        "Shared household essentials",
    ]
    assert "customization model did not return" in plan.priority_summary.lower()


def test_none_support_needs_plan_without_context_has_actionable_error() -> None:
    with pytest.raises(RuntimeError, match="customization_context"):
        _support_needs_plan_from_any(None)


def test_existing_support_needs_plan_is_preserved() -> None:
    context = _customization_context()
    expected = SupportNeedsPlan(
        profile=context.profile,
        comparison=context.comparison,
        priority_categories=context.baseline_categories,
        priority_summary="Structured customization succeeded.",
    )

    assert _support_needs_plan_from_any(expected) is expected
