import urllib.error

import submission_frontend.main as dashboard


def test_location_suggestions_include_typed_fallback_when_geocoders_fail(
    monkeypatch,
) -> None:
    def unavailable_fetcher(cleaned: str, limit: int):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(dashboard, "_fetch_nominatim_suggestions", unavailable_fetcher)
    monkeypatch.setattr(dashboard, "_fetch_photon_suggestions", unavailable_fetcher)

    suggestions = dashboard._fetch_location_suggestions("Brampton", limit=5)

    assert suggestions == [
        {
            "value": "Brampton",
            "label": "Use “Brampton” as typed",
            "source": "typed",
        }
    ]


def test_location_suggestions_use_broad_geocoder_results(monkeypatch) -> None:
    def empty_nominatim(cleaned: str, limit: int):
        return []

    def photon_result(cleaned: str, limit: int):
        return [
            {
                "value": "Beijing, China",
                "label": "Beijing, China",
                "source": "photon",
            }
        ]

    monkeypatch.setattr(dashboard, "_fetch_nominatim_suggestions", empty_nominatim)
    monkeypatch.setattr(dashboard, "_fetch_photon_suggestions", photon_result)

    suggestions = dashboard._fetch_location_suggestions("Beijing", limit=5)

    assert suggestions[0]["value"] == "Beijing, China"
    assert suggestions[0]["source"] == "photon"
    assert suggestions[-1]["value"] == "Beijing"
    assert suggestions[-1]["source"] == "typed"


def test_location_suggestions_dedupe_remote_and_typed(monkeypatch) -> None:
    def duplicate_nominatim(cleaned: str, limit: int):
        return [
            {
                "value": "Toronto, Ontario, Canada",
                "label": "Toronto, Ontario, Canada",
                "source": "openstreetmap",
            }
        ]

    monkeypatch.setattr(dashboard, "_fetch_nominatim_suggestions", duplicate_nominatim)
    monkeypatch.setattr(dashboard, "_fetch_photon_suggestions", lambda cleaned, limit: [])

    suggestions = dashboard._fetch_location_suggestions("Toronto", limit=5)
    values = [suggestion["value"] for suggestion in suggestions]

    assert values.count("Toronto, Ontario, Canada") == 1
    assert "Toronto" in values


def test_location_suggestions_do_not_use_hardcoded_city_list(monkeypatch) -> None:
    monkeypatch.setattr(dashboard, "_fetch_nominatim_suggestions", lambda cleaned, limit: [])
    monkeypatch.setattr(dashboard, "_fetch_photon_suggestions", lambda cleaned, limit: [])

    suggestions = dashboard._fetch_location_suggestions("San", limit=5)

    assert suggestions == [
        {
            "value": "San",
            "label": "Use “San” as typed",
            "source": "typed",
        }
    ]
