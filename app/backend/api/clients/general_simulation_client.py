import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8000"


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
        except (requests.RequestException, ValueError) as exc:
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
        except requests.RequestException as exc:
            logger.error("GeneralSimulation query failed: %s", exc)
            return {"error": str(exc)}

    def list_scenarios(self) -> dict[str, Any]:
        try:
            resp = self._session.get(
                f"{self.base_url}/admin/graph/scenarios",
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return {"scenarios": [str(item) for item in data]}
            return {"error": "Unexpected scenarios response shape"}
        except requests.Timeout:
            logger.error("GeneralSimulation list_scenarios timed out")
            return {"error": "Request timed out after 30s"}
        except requests.HTTPError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:500] if exc.response.text else ""
            logger.error("GeneralSimulation list_scenarios HTTP %s: %s", status, detail)
            return {"error": f"HTTP {status}: {detail}"}
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.error("GeneralSimulation list_scenarios failed: %s", exc)
            return {"error": str(exc)}

    def get_entities_geojson(
        self,
        *,
        bbox: str | None = None,
        ids: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if bbox:
            params["bbox"] = bbox
        if ids:
            params["ids"] = ",".join(ids)
        if limit is not None:
            params["limit"] = limit
        try:
            resp = self._session.get(
                f"{self.base_url}/admin/entities/geojson",
                params=params,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            return {"error": "Unexpected geojson response shape"}
        except requests.Timeout:
            logger.error("GeneralSimulation get_entities_geojson timed out")
            return {"error": "Request timed out after 60s"}
        except requests.HTTPError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:500] if exc.response.text else ""
            logger.error(
                "GeneralSimulation get_entities_geojson HTTP %s: %s", status, detail
            )
            return {"error": f"HTTP {status}: {detail}"}
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.error("GeneralSimulation get_entities_geojson failed: %s", exc)
            return {"error": str(exc)}

    def create_event(
        self,
        *,
        event_id: str,
        scenario_id: str,
        description: str,
        bbox: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Inject a SimulationEvent via ``POST /admin/graph/events`` (bbox required)."""
        payload: dict[str, Any] = {
            "id": event_id,
            "scenario_id": scenario_id,
            "description": description,
            "bbox": bbox,
            "affected_entity_ids": [],
            "attributes": attributes or {},
        }
        try:
            logger.info(
                "GeneralSimulation create_event: scenario=%s event=%s bbox=%s",
                scenario_id,
                event_id,
                bbox,
            )
            resp = self._session.post(
                f"{self.base_url}/admin/graph/events",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            return {"error": "Unexpected create_event response shape"}
        except requests.Timeout:
            logger.error("GeneralSimulation create_event timed out after %ss", self.timeout)
            return {"error": f"Request timed out after {self.timeout}s"}
        except requests.HTTPError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:500] if exc.response.text else ""
            logger.error("GeneralSimulation create_event HTTP %s: %s", status, detail)
            return {"error": f"HTTP {status}: {detail}"}
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.error("GeneralSimulation create_event failed: %s", exc)
            return {"error": str(exc)}

    def sync_spatial(self, scenario_id: str) -> dict[str, Any]:
        """Refresh AFFECTED_BY edges for a scenario's bbox overlays."""
        sid = (scenario_id or "").strip()
        if not sid:
            return {"error": "scenario_id is required"}
        try:
            resp = self._session.post(
                f"{self.base_url}/admin/graph/scenarios/{sid}/sync-spatial",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                return data
            return {"error": "Unexpected sync_spatial response shape"}
        except requests.Timeout:
            logger.error("GeneralSimulation sync_spatial timed out after %ss", self.timeout)
            return {"error": f"Request timed out after {self.timeout}s"}
        except requests.HTTPError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:500] if exc.response.text else ""
            logger.error("GeneralSimulation sync_spatial HTTP %s: %s", status, detail)
            return {"error": f"HTTP {status}: {detail}"}
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.error("GeneralSimulation sync_spatial failed: %s", exc)
            return {"error": str(exc)}
