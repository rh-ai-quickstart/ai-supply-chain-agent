from services import kpi_calculator as calc
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


def _parsed_sku(
    sku_id: str,
    on_hand: float,
    safety_stock: float = 50,
    reorder_point: float = 80,
    unit_price: float = 1000,
    daily_sales: float = 10,
    warehouse_id: str = "warehouse-inland-empire",
    linked_carrier_ids: list[str] | None = None,
) -> dict:
    return calc._parse_sku(
        _sku_item(
            sku_id,
            on_hand,
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            unit_price=unit_price,
            daily_sales=daily_sales,
            warehouse_id=warehouse_id,
            linked_carrier_ids=linked_carrier_ids,
        )
    )


def _shipment_feature(
    entity_id: str,
    promised: str | None = None,
    eta: str | None = None,
    status: str = "in_transit",
    geometry_type: str = "Point",
) -> dict:
    attrs = {}
    if promised is not None:
        attrs["promised_delivery_utc"] = promised
    if eta is not None:
        attrs["eta_utc"] = eta
    return {
        "type": "Feature",
        "id": entity_id,
        "geometry": {"type": geometry_type, "coordinates": [0, 0]},
        "properties": {
            "id": entity_id,
            "status": status,
            "attributes": attrs,
        },
    }


# --- helpers ---


def test_ratio_percent_clamps_and_handles_empty():
    assert calc._ratio_percent(1, 2) == 50
    assert calc._ratio_percent(0, 0) == 0.0
    assert calc._ratio_percent(5, 2) == 100
    assert calc._ratio_percent(-1, 2) == 0


def test_formatters():
    assert calc._format_percent(87.4) == "87%"
    assert calc._format_turnover(6.55) == "6.6x"
    assert calc._format_lost_sales_millions(0) == "$0.0M"
    assert calc._format_lost_sales_millions(1_350_000) == "$1.4M"


def test_parse_sku_and_shipment():
    sku = calc._parse_sku(_sku_item("sku-1", 12, linked_carrier_ids=["c1"]))
    assert sku["on_hand_qty"] == 12.0
    assert sku["linked_carrier_ids"] == ["c1"]

    shipment = calc._parse_shipment(
        _shipment_feature("v1", "2026-09-18T12:00:00Z", "2026-09-18T10:00:00Z")
    )
    assert shipment is not None
    assert shipment["id"] == "v1"
    assert shipment["promised_delivery_utc"] == "2026-09-18T12:00:00Z"

    assert calc._parse_shipment(_shipment_feature("bad", geometry_type="Polygon")) is None


def test_parse_utc():
    assert calc._parse_utc(None) is None
    assert calc._parse_utc("not-a-date") is None
    parsed = calc._parse_utc("2026-09-18T12:00:00Z")
    assert parsed is not None
    assert parsed.year == 2026


def test_is_sku_at_risk_and_effective_on_hand():
    sku = _parsed_sku(
        "sku-1",
        100,
        warehouse_id="warehouse-la",
        linked_carrier_ids=["carrier-a", "carrier-b"],
    )
    assert not calc._is_sku_at_risk(sku, set())
    assert calc._is_sku_at_risk(sku, {"sku-1"})
    assert calc._is_sku_at_risk(sku, {"warehouse-la"})
    assert calc._is_sku_at_risk(sku, {"carrier-a"})

    # No disruption → full on hand
    assert calc._effective_on_hand(sku, set()) == 100

    # Warehouse hit, no carrier hit → full penalty (0.35)
    warehouse_only = _parsed_sku("sku-2", 100, warehouse_id="warehouse-la")
    assert calc._effective_on_hand(warehouse_only, {"warehouse-la"}) == 65

    # One of two carriers disrupted → half penalty ratio
    assert calc._effective_on_hand(sku, {"carrier-a"}) == 100 * (1 - 0.35 * 0.5)


def test_pick_lost_sales_sources():
    assert calc._pick_lost_sales(100, 200) == (200, "max(sku_stockout,solver.var)")
    assert calc._pick_lost_sales(100, 0) == (100, "sku_stockout")
    assert calc._pick_lost_sales(0, 50) == (50, "solver.total_value_at_risk")
    assert calc._pick_lost_sales(0, 0) == (0.0, "simulation.none")


def test_on_time_helpers():
    timed = [
        calc._parse_shipment(
            _shipment_feature("v1", "2026-09-18T12:00:00Z", "2026-09-18T10:00:00Z")
        ),
        calc._parse_shipment(
            _shipment_feature("v2", "2026-09-19T08:00:00Z", "2026-09-19T09:30:00Z")
        ),
    ]
    assert timed[0] is not None and timed[1] is not None

    from_etas = calc._on_time_from_etas(timed, {"v2"})
    assert from_etas == (50, "shipment_eta")
    assert calc._on_time_from_etas([], set()) is None

    assert calc._on_time_from_impact(0) is None
    impact = calc._on_time_from_impact(0.5)
    assert impact is not None
    assert impact[1] == "heuristic.impact_score"

    healthy = calc._on_time_from_health(
        [{"status": "airborne"}, {"status": "delayed"}, {"status": "in_transit"}]
    )
    assert healthy[1] == "heuristic.entity_health"
    assert 88 <= healthy[0] <= 100


def test_trend_sentiment_and_apply_trend():
    assert calc._trend_sentiment("lostSales", "up") == "bad"
    assert calc._trend_sentiment("lostSales", "down") == "good"
    assert calc._trend_sentiment("reorderPoint", "up") == "caution"
    assert calc._trend_sentiment("inStock", "up") == "good"
    assert calc._trend_sentiment("inStock", "down") == "bad"
    assert calc._trend_sentiment("onTime", "neutral") == "neutral"

    current = calc._build_metric(80, calc._format_percent, "test")
    trended = calc._apply_trend("inStock", current, calc.DEFAULT_KPIS["inStock"])
    assert trended["trendDirection"] == "down"
    assert trended["trendSentiment"] == "bad"
    assert trended["trend"].startswith("▼")


def test_reorder_from_solver_fallbacks():
    ranked = calc._reorder_from_solver(
        {
            "response_options": [
                {"rank": 2, "estimated_impact_reduction": 0.1},
                {"rank": 1, "estimated_impact_reduction": 0.5},
            ]
        }
    )
    assert ranked[1] == "solver.response_options"
    assert ranked[0] == round(55 + 0.5 * 35)

    impact = calc._reorder_from_solver({"impact_score": 0.4})
    assert impact[1] == "heuristic.impact_score"

    default = calc._reorder_from_solver({})
    assert default == (calc.DEFAULT_KPIS["reorderPoint"]["numeric"], "simulation.default")


# --- compute_supply_chain_kpis ---


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
    assert result["data_quality"]["mode"] == "heuristic"


def test_on_time_falls_back_to_impact_score_without_etas():
    shipments = [
        _shipment_feature("v1", status="airborne"),
        _shipment_feature("v2", status="delayed"),
    ]
    result = compute_supply_chain_kpis(
        sku_items=[],
        geojson_features=shipments,
        solver={"impact_score": 0.5},
    )
    assert result["kpis"]["onTime"]["source"] == "heuristic.impact_score"
    assert result["kpis"]["onTime"]["numeric"] == round(96 - 0.5 * 40)


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
    assert result["kpis"]["lostSales"]["trendSentiment"] == "bad"


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
    assert result["kpis"]["lostSales"]["numeric"] == (80 - 65) * 1000
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


def test_turnover_uses_effective_inventory_under_disruption():
    skus = [
        _sku_item(
            "sku-1",
            on_hand=100,
            unit_price=10,
            daily_sales=10,
            linked_carrier_ids=["carrier-a"],
        ),
    ]
    result = compute_supply_chain_kpis(
        sku_items=skus,
        geojson_features=[],
        affected_entities=["carrier-a"],
    )
    # annual_sales = 3650; inventory = 100 * 0.65 * 10 = 650; turnover ≈ 5.6
    expected = round((3650 / 650) * 10) / 10
    assert result["kpis"]["turnover"]["numeric"] == expected
    assert result["kpis"]["turnover"]["source"] == "inventory_sku.avg_daily_sales_30d"


def test_skips_unsupported_geojson_geometry():
    features = [
        _shipment_feature("v1", "2026-09-18T12:00:00Z", "2026-09-18T10:00:00Z"),
        _shipment_feature(
            "poly",
            "2026-09-18T12:00:00Z",
            "2026-09-18T10:00:00Z",
            geometry_type="Polygon",
        ),
    ]
    result = compute_supply_chain_kpis(
        sku_items=[],
        geojson_features=features,
        affected_entities=["v1"],
    )
    assert result["data_quality"]["shipment_count"] == 1
