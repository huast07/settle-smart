import asyncio

import pytest
from fastapi.testclient import TestClient

import submission_frontend.main as dashboard


def _payload() -> dict[str, object]:
    return {
        "age": 34,
        "family_size": 4,
        "origin_location": "Toronto, Ontario, Canada",
        "destination_location": "San Francisco, California, United States",
    }


def test_agent_timeout_seconds_uses_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBMISSION_FRONTEND_AGENT_TIMEOUT", "0.25")

    assert dashboard._agent_timeout_seconds() == 0.25


def test_agent_timeout_seconds_rejects_invalid_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUBMISSION_FRONTEND_AGENT_TIMEOUT", "not-a-number")

    with pytest.raises(RuntimeError, match="positive number"):
        dashboard._agent_timeout_seconds()


@pytest.mark.asyncio
async def test_recommendations_from_agent_raises_named_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def slow_backend_agent(prompt: str) -> dict[str, object]:
        await asyncio.sleep(0.05)
        return {}

    monkeypatch.setenv("SUBMISSION_FRONTEND_AGENT_TIMEOUT", "0.01")
    monkeypatch.setattr(dashboard, "_invoke_local_backend_agent", slow_backend_agent)

    with pytest.raises(dashboard.BackendAgentTimeoutError, match="0.01 seconds"):
        await dashboard._recommendations_from_agent(
            dashboard.NewcomerIntake.model_validate(_payload())
        )


def test_recommendations_endpoint_returns_504_for_agent_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def timeout_agent(
        intake: dashboard.NewcomerIntake,
    ) -> dict[str, object]:
        raise dashboard.BackendAgentTimeoutError(12)

    monkeypatch.setattr(dashboard, "_recommendations_from_agent", timeout_agent)

    response = TestClient(dashboard.app).post("/api/recommendations", json=_payload())
    body = response.json()

    assert response.status_code == 504
    assert body["error"] == "backend_agent_timeout"
    assert "12 seconds" in body["message"]
    assert body["suggested_fixes"]
