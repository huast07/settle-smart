from app.agent import (
    PARALLEL_PROGRAM_SEARCH_AGENTS,
    ProgramSearchPrompt,
    ProgramSearchResult,
    _program_search_result_from_agent_output,
    _merge_parallel_program_search_results,
)


def test_program_search_result_accepts_missing_evidence_summary() -> None:
    result = ProgramSearchResult.model_validate(
        {
            "destination": "San Francisco, California, United States",
            "queries_used": ["San Francisco transit rewards official"],
            "discovered_programs": [
                {
                    "program_name": "Example Transit Discount",
                    "provider": "Example Transit Agency",
                    "category": "Transit",
                    "source_url": "https://example.test/transit",
                    "eligibility_notes": "Verify residency or service-area requirements.",
                    "signup_path": "Apply on the official transit agency website.",
                }
            ],
        }
    )

    program = result.discovered_programs[0]
    assert program.evidence_summary == (
        "Apply on the official transit agency website. "
        "Verify residency or service-area requirements. "
        "Source: https://example.test/transit"
    )
    assert program.confidence == "medium"


def test_program_search_result_accepts_empty_program_list() -> None:
    result = ProgramSearchResult.model_validate(
        {
            "destination": "San Francisco, California, United States",
            "queries_used": [],
            "discovered_programs": [],
        }
    )

    assert result.search_summary == ""
    assert result.discovered_programs == []


def test_parallel_program_search_agents_are_category_scoped() -> None:
    names = [agent.name for agent in PARALLEL_PROGRAM_SEARCH_AGENTS]

    assert names == [
        "discover_food_household_programs",
        "discover_transit_programs",
        "discover_banking_credit_programs",
        "discover_health_pharmacy_programs",
        "discover_housing_utilities_programs",
        "discover_telecom_programs",
    ]
    assert len(set(names)) == len(names)


def test_parallel_program_search_merge_dedupes_programs() -> None:
    event = _merge_parallel_program_search_results(
        {
            "food": {
                "destination": "Toronto, Ontario, Canada",
                "queries_used": ["Toronto grocery rewards official"],
                "discovered_programs": [
                    {
                        "program_name": "Example Rewards",
                        "provider": "Example Grocer",
                        "category": "Food and groceries",
                        "source_url": "https://example.test/rewards",
                        "evidence_summary": "Official loyalty page.",
                    }
                ],
                "search_summary": "Food search found one program.",
                "source_notes": ["Food branch used official pages."],
            },
            "household_duplicate": {
                "destination": "Toronto, Ontario, Canada",
                "queries_used": ["Toronto household rewards official"],
                "discovered_programs": [
                    {
                        "program_name": "Example Rewards",
                        "provider": "Example Grocer",
                        "category": "Food and groceries",
                        "source_url": "https://example.test/rewards",
                        "evidence_summary": "Duplicate official loyalty page.",
                    }
                ],
                "search_summary": "Household search repeated the same program.",
                "source_notes": ["Household branch used official pages."],
            },
        }
    )

    merged = ProgramSearchResult.model_validate(event.output)

    assert merged.destination == "Toronto, Ontario, Canada"
    assert merged.queries_used == [
        "Toronto grocery rewards official",
        "Toronto household rewards official",
    ]
    assert len(merged.discovered_programs) == 1
    assert "Food search found one program." in merged.search_summary
    assert "Household search repeated the same program." in merged.search_summary
    assert event.actions.state_delta["program_search_result"]["destination"] == (
        "Toronto, Ontario, Canada"
    )


def test_program_search_text_notes_are_converted_to_structured_result() -> None:
    prompt = ProgramSearchPrompt(
        destination="San Francisco, California, United States",
        search_objective="Find verified programs.",
        priority_categories=[],
        suggested_queries=[
            "San Francisco grocery rewards official",
            "San Francisco transit discount official",
        ],
        verification_rules=["Prefer official pages."],
    )

    result = _program_search_result_from_agent_output(
        output=(
            "Program: Example Rewards; Provider: Example Grocer; "
            "Category: Food and groceries; Official URL: https://example.test; "
            "Evidence: Official loyalty page; Eligibility: Free account; "
            "Fees: No fee; Signup: Join online; Confidence: high"
        ),
        prompt=prompt,
        search_agent_name="discover_food_household_programs",
    )

    assert result.destination == "San Francisco, California, United States"
    assert result.queries_used == ["San Francisco grocery rewards official"]
    assert result.discovered_programs[0].program_name == "Example Rewards"
    assert result.discovered_programs[0].source_url == "https://example.test"
    assert result.discovered_programs[0].confidence == "high"
