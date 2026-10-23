from unittest.mock import MagicMock

from services.kpi_service import KpiService


def _mock_gen_sim():
    gen_sim = MagicMock()
    gen_sim.list_entities.return_value = {
        "success": True,
        "items": [
            {
                "id": "sku-1",
                "attributes": {
                    "sku": "SKU-1",
                    "warehouse_id": "warehouse-inland-empire",
                    "on_hand_qty": 120,
                    "safety_stock": 50,
                    "reorder_point": 80,
                    "unit_price_usd": 1000,
                    "avg_daily_sales_30d": 10,
                    "linked_carrier_ids": [],
                },
            }
        ],
    }
    gen_sim.get_entities_geojson.return_value = {
        "success": True,
        "geojson": {"type": "FeatureCollection", "features": []},
    }
    gen_sim.run_simulation = MagicMock()
    return gen_sim


def test_get_kpis_does_not_run_simulation():
    gen_sim = _mock_gen_sim()
    service = KpiService(general_simulation_service=gen_sim)

    result = service.get_kpis(scenario_id="opensky-uk-closure-001", bbox="-1,2,3,4")

    assert result["success"] is True
    gen_sim.run_simulation.assert_not_called()
    gen_sim.get_entities_geojson.assert_called_once_with(
        bbox="-1,2,3,4",
        limit=500,
        entity_type="moving_entity",
    )


def test_compute_kpis_with_solver_snapshot_skips_simulation():
    gen_sim = _mock_gen_sim()
    service = KpiService(general_simulation_service=gen_sim)

    result = service.compute_kpis(
        scenario_id="supply-chain-port-strike-la",
        bbox="-1,2,3,4",
        solver={"impact_score": 0.65, "total_value_at_risk": 1_000_000},
        affected_entities=["vessel-pacific-star"],
    )

    assert result["success"] is True
    assert result["data_quality"]["has_solver"] is True
    gen_sim.run_simulation.assert_not_called()
    assert result["kpis"]["lostSales"]["numeric"] > 0
