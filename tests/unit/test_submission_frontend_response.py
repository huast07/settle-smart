import re
import shutil
import subprocess

import pytest

import submission_frontend.main as dashboard


def _inline_scripts() -> list[str]:
    return re.findall(r"<script>(.*?)</script>", dashboard.INDEX_HTML, flags=re.DOTALL)


def test_shape_agent_response_includes_destination_summary() -> None:
    intake = dashboard.NewcomerIntake(
        age=34,
        family_size=4,
        origin_location="Toronto, Ontario, Canada",
        destination_location="San Francisco, California, United States",
    )
    artifacts = {
        "plan": {
            "opening_summary": "A practical first pass.",
            "comparison_context_used": "Grocery, transit, and banking norms differ.",
            "priority_categories": ["Food and groceries", "Transit", "Banking"],
            "recommendations": [
                {
                    "program_name": "Example Rewards",
                    "provider": "Example Provider",
                    "category": "Food and groceries",
                    "why_recommended": "Useful for household purchases.",
                    "confidence": "medium",
                }
            ],
        },
        "event_count": 3,
    }

    response = dashboard._shape_agent_response(intake, artifacts, mode="backend_agent")

    assert response["destination_summary"]["title"] == (
        "Destination snapshot: San Francisco, California, United States"
    )
    assert response["destination_summary"]["focus"] == (
        "Food and groceries, Transit, Banking"
    )
    assert "Household size: 4" in response["destination_summary"]["household"]
    assert "tone" not in response["destination_summary"]
    assert "Toronto" in response["destination_summary"]["summary"]
    assert "San Francisco" in response["destination_summary"]["summary"]


def test_agent_prompt_includes_telecom_and_healthcare_programs() -> None:
    intake = dashboard.NewcomerIntake(
        age=29,
        family_size=1,
        origin_location="Beijing, China",
        destination_location="Brampton, Ontario, Canada",
    )

    prompt = dashboard._build_agent_prompt(intake)

    assert "cellular or telecommunications" in prompt
    assert "internet access" in prompt
    assert "pharmacy" in prompt
    assert "government healthcare benefits" in prompt


def test_dashboard_html_has_no_frontend_only_decision_controls() -> None:
    assert "data-action=\"approve\"" not in dashboard.INDEX_HTML
    assert "data-action=\"reject\"" not in dashboard.INDEX_HTML
    assert "Pending manager decision" not in dashboard.INDEX_HTML
    assert "citySummaryTitle" in dashboard.INDEX_HTML
    assert "citySummaryHousehold" in dashboard.INDEX_HTML
    assert "Welcome theme" not in dashboard.INDEX_HTML
    assert "citySummaryTone" not in dashboard.INDEX_HTML
    assert "themeChip" not in dashboard.INDEX_HTML
    assert "--destination-image" in dashboard.INDEX_HTML
    assert "has-destination-image" in dashboard.INDEX_HTML


def test_dashboard_inline_javascript_parses_and_registers_form_navigation(
    tmp_path,
) -> None:
    node_path = shutil.which("node")
    if not node_path:
        pytest.skip("Node.js is required for the dashboard JavaScript syntax check.")

    scripts = _inline_scripts()
    assert scripts
    combined_script = "\n".join(scripts)
    assert 'nextPlaces.addEventListener("click"' in combined_script

    for index, script in enumerate(scripts):
        script_path = tmp_path / f"dashboard-inline-{index}.js"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            [node_path, "--check", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
