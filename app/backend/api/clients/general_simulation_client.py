from typing import Any, Callable, Optional

from logging_config import getLogger
import requests

logger = getLogger(__name__)

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

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: int,
        label: str,
        validate: Callable[[Any], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """HTTP JSON from gen-sim with shared timeout/HTTP error handling."""
        try:
            resp = self._session.request(
                method,
                f"{self.base_url}{path}",
                params=params or {},
                json=json_body,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            if validate is not None:
                return validate(data)
            if isinstance(data, dict):
                return data
            return {"error": f"Unexpected {label} response shape"}
        except requests.Timeout:
            logger.error("GeneralSimulation %s timed out", label)
            return {"error": f"Request timed out after {timeout}s"}
        except requests.HTTPError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:500] if exc.response.text else ""
            logger.error("GeneralSimulation %s HTTP %s: %s", label, status, detail)
            return {"error": f"HTTP {status}: {detail}"}
        except (requests.RequestException, ValueError, TypeError) as exc:
            logger.error("GeneralSimulation %s failed: %s", label, exc)
            return {"error": str(exc)}

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
        logger.info(
            "GeneralSimulation query: scenario=%s question=%r",
            scenario_id,
            question[:80],
        )
        return self._request_json(
            "POST",
            "/query",
            json_body=payload,
            timeout=self.timeout,
            label="query",
        )

    def list_scenarios(self) -> dict[str, Any]:
        def _validate(data: Any) -> dict[str, Any]:
            if isinstance(data, list):
                return {"scenarios": [str(item) for item in data]}
            return {"error": "Unexpected scenarios response shape"}

        return self._request_json(
            "GET",
            "/admin/graph/scenarios",
            timeout=30,
            label="list_scenarios",
            validate=_validate,
        )

    def list_entities(
        self,
        *,
        entity_type: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if entity_type:
            params["type"] = entity_type
        return self._request_json(
            "GET",
            "/admin/entities",
            params=params,
            timeout=60,
            label="list_entities",
        )

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
        return self._request_json(
            "GET",
            "/admin/entities/geojson",
            params=params,
            timeout=60,
            label="get_entities_geojson",
        )

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
        logger.info(
            "GeneralSimulation create_event: scenario=%s event=%s bbox=%s",
            scenario_id,
            event_id,
            bbox,
        )
        return self._request_json(
            "POST",
            "/admin/graph/events",
            json_body=payload,
            timeout=self.timeout,
            label="create_event",
        )

    def sync_spatial(self, scenario_id: str) -> dict[str, Any]:
        """Refresh AFFECTED_BY edges for a scenario's bbox overlays."""
        sid = (scenario_id or "").strip()
        if not sid:
            return {"error": "scenario_id is required"}
        return self._request_json(
            "POST",
            f"/admin/graph/scenarios/{sid}/sync-spatial",
            timeout=self.timeout,
            label="sync_spatial",
        )
