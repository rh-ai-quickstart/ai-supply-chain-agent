"""Optional OpenAI SDK autologging for backend model calls."""

from __future__ import annotations

import logging
import os
import socket
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

LOGGER = logging.getLogger(__name__)
STARTUP_TRACE_NAME = "agent.backend.startup"


class MlflowTracing:
    """Enable model autologging plus application chat and retrieval spans."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        tracking_uri: str | None = None,
        experiment_name: str = "supply-chain-disruption-evals",
        git_commit: str = "unknown",
    ) -> None:
        self.enabled = enabled
        self.tracking_uri = tracking_uri or ""
        self.experiment_name = experiment_name
        self.git_commit = git_commit
        self.session_id = f"{socket.gethostname()}-{uuid.uuid4().hex}"
        self.started_at_ms = int(time.time() * 1000)
        self._mlflow: Any | None = None

    def initialize(self) -> None:
        if not self.enabled:
            return
        try:
            import mlflow

            if self.tracking_uri:
                mlflow.set_tracking_uri(self.tracking_uri)
            elif not os.getenv("MLFLOW_TRACKING_URI"):
                raise RuntimeError("MLFLOW_TRACKING_URI is required when backend tracing is enabled")
            mlflow.set_experiment(self.experiment_name)
            mlflow.openai.autolog()
            self._mlflow = mlflow

            # This marker identifies the backend restart boundary.
            with mlflow.start_span(name=STARTUP_TRACE_NAME, span_type="CHAIN") as span:
                span.set_inputs({"backend_session_id": self.session_id})
                span.set_outputs(
                    {
                        "backend_session_id": self.session_id,
                        "backend_started_at_ms": self.started_at_ms,
                        "backend_host": socket.gethostname(),
                        "git_commit": self.git_commit,
                    }
                )
                mlflow.update_current_trace(
                    tags={
                        "trace_kind": "backend_startup",
                        "backend_session_id": self.session_id,
                        "backend_host": socket.gethostname(),
                    },
                    metadata={"git_commit": self.git_commit},
                )

            LOGGER.info(
                "MLflow tracing enabled: experiment=%s session=%s started_at_ms=%d",
                self.experiment_name,
                self.session_id,
                self.started_at_ms,
            )
        except Exception:
            self.enabled = False
            self._mlflow = None
            LOGGER.exception("MLflow OpenAI autologging setup failed; continuing with tracing disabled")

    @contextmanager
    def span(
        self,
        *,
        name: str,
        span_type: str,
        inputs: dict[str, Any] | None = None,
    ) -> Iterator[Any | None]:
        """Create a child span when tracing is enabled; otherwise act as a no-op."""
        if not self.enabled or self._mlflow is None:
            yield None
            return

        with self._mlflow.start_span(name=name, span_type=span_type) as span:
            if inputs is not None:
                span.set_inputs(inputs)
            yield span
