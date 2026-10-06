from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from services.general_simulation_service import GeneralSimulationService
from services.kpi_calculator import compute_supply_chain_kpis

KPI_GEOJSON_LIMIT = 500
KPI_ENTITY_TYPE = "moving_entity"


class KpiService:
    def __init__(self, general_simulation_service: Optional[GeneralSimulationService] = None):
        self._gen_sim = general_simulation_service or GeneralSimulationService()

    def _fetch_source_data(self, bbox: str | None) -> dict[str, Any]:
        with ThreadPoolExecutor(max_workers=2) as pool:
            sku_future = pool.submit(
                self._gen_sim.list_entities,
                entity_type="inventory_sku",
                limit=500,
            )
            geo_future = pool.submit(
                self._gen_sim.get_entities_geojson,
                bbox=bbox,
                limit=KPI_GEOJSON_LIMIT,
                entity_type=KPI_ENTITY_TYPE,
            )
            sku_result = sku_future.result()
            geo_result = geo_future.result()

        if not sku_result.get("success"):
            return sku_result
        if not geo_result.get("success"):
            return geo_result

        return {
            "success": True,
            "sku_items": sku_result.get("items") or [],
            "features": (geo_result.get("geojson") or {}).get("features") or [],
        }

    def compute_kpis(
        self,
        *,
        scenario_id: str | None = None,
        bbox: str | None = None,
        solver: dict[str, Any] | None = None,
        affected_entities: list[str] | None = None,
    ) -> dict[str, Any]:
        """Compute KPIs from seeded entities. Never runs the LLM impact query."""
        source = self._fetch_source_data(bbox)
        if not source.get("success"):
            return source

        computed = compute_supply_chain_kpis(
            sku_items=source["sku_items"],
            geojson_features=source["features"],
            solver=solver,
            affected_entities=affected_entities or [],
        )

        return {
            "success": True,
            "scenario_id": scenario_id or "",
            **computed,
        }

    def get_kpis(
        self,
        *,
        scenario_id: str | None = None,
        bbox: str | None = None,
    ) -> dict[str, Any]:
        """Baseline KPIs only (no disruption overlay)."""
        return self.compute_kpis(scenario_id=scenario_id, bbox=bbox)
