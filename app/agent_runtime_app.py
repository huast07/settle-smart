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
import logging
import os
from typing import Any

import vertexai
from dotenv import load_dotenv
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.auth.credentials import AnonymousCredentials
from google.cloud import logging as google_cloud_logging
from vertexai.agent_engines.templates.adk import AdkApp

from app.agent import app as adk_app
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

# Load environment variables from .env file at runtime
load_dotenv()


def _is_integration_test() -> bool:
    return os.environ.get("INTEGRATION_TEST", "").upper() == "TRUE"


class _LocalFeedbackLogger:
    def log_struct(self, payload: dict[str, Any], severity: str = "INFO") -> None:
        logging.getLogger(__name__).info("%s feedback: %s", severity, payload)


class AgentEngineApp(AdkApp):
    def set_up(self) -> None:
        """Initialize the agent engine app with logging and telemetry."""
        if _is_integration_test():
            from google.adk.memory.in_memory_memory_service import (
                InMemoryMemoryService,
            )
            from google.adk.runners import Runner
            from google.adk.sessions.in_memory_session_service import (
                InMemorySessionService,
            )

            artifact_service = InMemoryArtifactService()
            memory_service = InMemoryMemoryService()
            session_service = InMemorySessionService()
            runner = Runner(
                app=adk_app,
                session_service=session_service,
                artifact_service=artifact_service,
                memory_service=memory_service,
            )
            self._tmpl_attrs["artifact_service"] = artifact_service
            self._tmpl_attrs["memory_service"] = memory_service
            self._tmpl_attrs["session_service"] = session_service
            self._tmpl_attrs["runner"] = runner
            self._tmpl_attrs["in_memory_artifact_service"] = artifact_service
            self._tmpl_attrs["in_memory_memory_service"] = memory_service
            self._tmpl_attrs["in_memory_session_service"] = session_service
            self._tmpl_attrs["in_memory_runner"] = runner
            logging.basicConfig(level=logging.INFO)
            self.logger = _LocalFeedbackLogger()
            if gemini_location:
                os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location
            return

        vertexai.init()
        setup_telemetry()
        super().set_up()
        logging.basicConfig(level=logging.INFO)
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)
        if gemini_location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = gemini_location

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        """Collect and log feedback."""
        feedback_obj = Feedback.model_validate(feedback)
        self.logger.log_struct(feedback_obj.model_dump(), severity="INFO")

    def register_operations(self) -> dict[str, list[str]]:
        """Registers the operations of the Agent."""
        operations = super().register_operations()
        operations[""] = [*operations.get("", []), "register_feedback"]
        return operations

    def clone(self) -> "AgentEngineApp":
        """Returns a clone of the Agent Runtime application."""
        return self


gemini_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
_agent_runtime: AgentEngineApp | None = None


def _prepare_integration_vertexai() -> None:
    if not _is_integration_test():
        return

    vertexai.init(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", "local-test-project"),
        location=gemini_location or os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1"),
        credentials=AnonymousCredentials(),
    )


def get_agent_runtime() -> AgentEngineApp:
    global _agent_runtime
    if _agent_runtime is None:
        _prepare_integration_vertexai()
        _agent_runtime = AgentEngineApp(
            app=adk_app,
            artifact_service_builder=lambda: (
                GcsArtifactService(bucket_name=logs_bucket_name)
                if logs_bucket_name
                else InMemoryArtifactService()
            ),
        )
    return _agent_runtime


def __getattr__(name: str) -> Any:
    if name == "agent_runtime":
        return get_agent_runtime()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["AgentEngineApp", "agent_runtime", "get_agent_runtime"]
