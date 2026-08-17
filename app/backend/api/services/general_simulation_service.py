from typing import Any, Optional

from clients.general_simulation_client import GeneralSimulationClient
from logging_config import getLogger

logger = getLogger(__name__)


class GeneralSimulationService:
    def __init__(self, client: Optional[GeneralSimulationClient] = None):
        self._client = client or GeneralSimulationClient()

    def check_health(self) -> dict[str, Any]:
        return self._client.health()

    def run_simulation(
        self,
        question: str,
        scenario_id: str,
    ) -> dict[str, Any]:
        if not question or not question.strip():
            return {"success": False, "error": "question is required"}
        if not scenario_id or not scenario_id.strip():
            return {"success": False, "error": "scenario_id is required"}

        result = self._client.query(question.strip(), scenario_id.strip())

        if "error" in result:
            return {"success": False, "error": result["error"]}

        return {
            "success": True,
            "answer": result.get("answer", ""),
            "scenario_id": result.get("scenario_id", scenario_id),
            "question": result.get("question", question),
            "affected_entities": result.get("affected_entities", []),
            "solver": result.get("solver", {}),
            "tool_call_trace": result.get("tool_call_trace", []),
        }

    def list_scenarios(self) -> dict[str, Any]:
        result = self._client.list_scenarios()
        if "error" in result:
            return {"success": False, "error": result["error"], "scenarios": []}
        return {
            "success": True,
            "scenarios": result.get("scenarios", []),
        }

    def get_entities_geojson(
        self,
        *,
        bbox: str | None = None,
        ids: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        result = self._client.get_entities_geojson(bbox=bbox, ids=ids, limit=limit)
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {
            "success": True,
            "geojson": result,
        }
