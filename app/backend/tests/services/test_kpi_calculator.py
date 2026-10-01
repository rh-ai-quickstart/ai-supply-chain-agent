from services.kpi_calculator import compute_supply_chain_kpis


def _sku_item(
    sku_id: str,
    on_hand: float,
    safety_stock: float = 50,
    reorder_point: float = 80,
    unit_price: float = 1000,
    daily_sales: float = 10,
    warehouse_id: str = "warehouse-inland-empire",
    linked_carrier_ids: list[str] | None = None,
) -> dict:
    return {
        "id": sku_id,
        "type": "inventory_sku",
        "attributes": {
            "sku": sku_id,
            "warehouse_id": warehouse_id,
            "on_hand_qty": on_hand,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "unit_price_usd": unit_price,
            "avg_daily_sales_30d": daily_sales,
            "linked_carrier_ids": linked_carrier_ids or [],
        },
    }


def _shipment_feature(
    entity_id: str,
    promised: str,
    eta: str,
    status: str = "in_transit",
) -> dict:
    return {
        "type": "Feature",
        "id": entity_id,
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "properties": {
            "id": entity_id,
            "status": status,
            "attributes": {
                "promised_delivery_utc": promised,
                "eta_utc": eta,
            },
        },
    }


def test_healthy_baseline_without_data():
    result = compute_supply_chain_kpis(sku_items=[], geojson_features=[])
    assert result["data_quality"]["mode"] == "healthy_baseline"
    assert result["kpis"]["inStock"]["value"] == "100%"
    assert result["kpis"]["onTime"]["value"] == "100%"
    assert result["kpis"]["turnover"]["value"] == "6.5x"
    assert result["kpis"]["lostSales"]["value"] == "$0.0M"
    assert result["kpis"]["reorderPoint"]["value"] == "0%"
    assert result["kpis"]["inStock"]["trend"] == ""


def test_healthy_baseline_with_skus_but_no_disruption():
    skus = [
        _sku_item("sku-1", 120, safety_stock=50, reorder_point=80),
        _sku_item("sku-2", 30, safety_stock=50, reorder_point=80),
    ]
    result = compute_supply_chain_kpis(sku_items=skus, geojson_features=[])
    assert result["data_quality"]["mode"] == "healthy_baseline"
    assert result["data_quality"]["sku_count"] == 2
    assert result["kpis"]["inStock"]["numeric"] == 100
    assert result["kpis"]["reorderPoint"]["numeric"] == 0


def test_on_time_from_shipment_etas_under_disruption():
    shipments = [
        _shipment_feature("v1", "2026-09-18T12:00:00Z", "2026-09-18T10:00:00Z"),
        _shipment_feature("v2", "2026-09-19T08:00:00Z", "2026-09-19T09:30:00Z"),
    ]
    result = compute_supply_chain_kpis(
        sku_items=[],
        geojson_features=shipments,
        affected_entities=["v2"],
    )
    assert result["kpis"]["onTime"]["numeric"] == 50
    assert result["kpis"]["onTime"]["source"] == "shipment_eta"
    assert result["kpis"]["onTime"]["trendDirection"] == "down"


def test_disruption_reduces_in_stock_and_raises_lost_sales():
    skus = [
        _sku_item(
            "sku-1",
            120,
            safety_stock=80,
            linked_carrier_ids=["vessel-pacific-star"],
        ),
        _sku_item("sku-2", 200, safety_stock=50),
    ]
    solver = {"impact_score": 0.65, "total_value_at_risk": 1_234_567}
    result = compute_supply_chain_kpis(
        sku_items=skus,
        geojson_features=[],
        solver=solver,
        affected_entities=["vessel-pacific-star"],
    )
    assert result["data_quality"]["mode"] == "simulation_backed"
    assert result["kpis"]["inStock"]["numeric"] < 100
    assert result["kpis"]["lostSales"]["numeric"] > 1_000_000
    assert "solver" in result["kpis"]["lostSales"]["source"]
    assert result["kpis"]["inStock"]["trendDirection"] == "down"
    assert result["kpis"]["lostSales"]["trendDirection"] == "up"


def test_warehouse_disruption_reduces_in_stock_and_raises_lost_sales():
    skus = [
        _sku_item("sku-1", 100, safety_stock=80, warehouse_id="warehouse-la"),
        _sku_item("sku-2", 200, safety_stock=50, warehouse_id="warehouse-other"),
    ]
    result = compute_supply_chain_kpis(
        sku_items=skus,
        geojson_features=[],
        affected_entities=["warehouse-la"],
    )
    # 100 * 0.65 = 65 < safety 80 → sku-1 out of stock; sku-2 untouched
    assert result["kpis"]["inStock"]["numeric"] == 50
    assert result["kpis"]["lostSales"]["numeric"] > 0
    assert result["kpis"]["lostSales"]["source"] == "sku_stockout"


def test_reorder_uses_effective_on_hand_under_carrier_disruption():
    skus = [
        _sku_item(
            "sku-1",
            100,
            safety_stock=20,
            reorder_point=70,
            linked_carrier_ids=["vessel-pacific-star"],
        ),
    ]
    # 100 * 0.65 = 65 <= reorder 70 → counts as needing reorder
    result = compute_supply_chain_kpis(
        sku_items=skus,
        geojson_features=[],
        affected_entities=["vessel-pacific-star"],
    )
    assert result["kpis"]["reorderPoint"]["numeric"] == 100
    assert result["kpis"]["reorderPoint"]["trendDirection"] == "up"
    assert result["kpis"]["reorderPoint"]["trendSentiment"] == "caution"


def test_lost_sales_uses_max_not_sum_when_both_present():
    skus = [
        _sku_item(
            "sku-1",
            50,
            safety_stock=100,
            unit_price=1000,
            linked_carrier_ids=["vessel-pacific-star"],
        ),
    ]
    # effective = 50 * 0.65 = 32.5; shortfall = 100 - 32.5 = 67.5 → $67,500
    solver_var = 1_000_000
    result = compute_supply_chain_kpis(
        sku_items=skus,
        geojson_features=[],
        solver={"total_value_at_risk": solver_var},
        affected_entities=["vessel-pacific-star"],
    )
    assert result["kpis"]["lostSales"]["numeric"] == solver_var
    assert result["kpis"]["lostSales"]["source"] == "max(sku_stockout,solver.var)"
    assert result["kpis"]["lostSales"]["numeric"] != 67_500 + solver_var
