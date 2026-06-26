from app.agent import ProgramSearchResult


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
