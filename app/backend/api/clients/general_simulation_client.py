import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = os.getenv("GENERAL_SIMULATION_BASE_URL", "http://localhost:8000")


class GeneralSimulationClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = 120,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = (base_url or _DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = session or requests.Session()

    def health(self) -> dict[str, Any]:
        try:
            resp = self._session.get(
                f"{self.base_url}/health",
                timeout=10,
            )
            resp.raise_for_status()
            return dict(resp.json())
        except Exception as exc:
            logger.warning("GeneralSimulation health check failed: %s", exc)
            return {"status": "unreachable", "db": "unknown"}

    def query(
        self,
        question: str,
        scenario_id: str,
    ) -> dict[str, Any]:
        payload = {
            "question": question,
            "scenario_id": scenario_id,
        }
        try:
            logger.info(
                "GeneralSimulation query: scenario=%s question=%r",
                scenario_id,
                question[:80],
            )
            resp = self._session.post(
                f"{self.base_url}/query",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return dict(resp.json())
        except requests.Timeout:
            logger.error("GeneralSimulation query timed out after %ss", self.timeout)
            return {"error": f"Request timed out after {self.timeout}s"}
        except requests.HTTPError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:500] if exc.response.text else ""
            logger.error("GeneralSimulation query HTTP %s: %s", status, detail)
            return {"error": f"HTTP {status}: {detail}"}
        except Exception as exc:
            logger.error("GeneralSimulation query failed: %s", exc)
            return {"error": str(exc)}
