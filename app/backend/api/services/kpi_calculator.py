"""Supply-chain KPI computation from simulation entity data and solver output.

Public entrypoint: ``compute_supply_chain_kpis``.

Metrics (see docs/KPIS.md for full formulas and modes):

- ``inStock``: % SKUs with effective on-hand >= safety stock
- ``onTime``: % timed shipments with eta <= promised (else impact/health heuristic)
- ``turnover``: annualized sales / effective inventory value (clamped 2–12x)
- ``lostSales``: max(SKU stockout $, solver VaR) during disruption
- ``reorderPoint``: % SKUs with effective on-hand <= reorder point

Healthy baseline (no solver, no affected entities) returns fixed defaults.
Disruption applies a 0.35 penalty to at-risk SKU on-hand (warehouse / SKU id /
linked carriers). Trends compare disrupted values to those defaults.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

HEALTHY_STATUSES = frozenset({"airborne", "in_transit", "on_ground"})
WAREHOUSE_OR_SKU_PENALTY = 0.35

DEFAULT_KPIS = {
    "inStock": {"value": "100%", "numeric": 100},
    "onTime": {"value": "100%", "numeric": 100},
    "turnover": {"value": "6.5x", "numeric": 6.5},
    "lostSales": {"value": "$0.0M", "numeric": 0},
    "reorderPoint": {"value": "0%", "numeric": 0},
}

# trendDirection → sentiment per metric (higher lostSales/reorder is worse)
_TREND_SENTIMENT = {
    "lostSales": {"up": "bad", "down": "good"},
    "reorderPoint": {"up": "caution", "down": "good"},
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def _round1(value: float) -> float:
    return round(value * 10) / 10


def _ratio_percent(count: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return _clamp((count / total) * 100, 0, 100)


def _format_percent(value: float) -> str:
    return f"{round(value)}%"


def _format_turnover(value: float) -> str:
    return f"{_round1(value)}x"


def _format_lost_sales_millions(amount: float) -> str:
    if amount <= 0:
        return "$0.0M"
    return f"${_round1(amount / 1_000_000)}M"


def _float_or_zero(value: Any) -> float:
    return float(value or 0)


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_sku(item: dict[str, Any]) -> dict[str, Any]:
    attrs = item.get("attributes") or {}
    return {
        "id": item.get("id"),
        "sku": attrs.get("sku"),
        "warehouse_id": attrs.get("warehouse_id"),
        "on_hand_qty": _float_or_zero(attrs.get("on_hand_qty")),
        "safety_stock": _float_or_zero(attrs.get("safety_stock")),
        "reorder_point": _float_or_zero(attrs.get("reorder_point")),
        "unit_price_usd": _float_or_zero(attrs.get("unit_price_usd")),
        "avg_daily_sales_30d": _float_or_zero(attrs.get("avg_daily_sales_30d")),
        "linked_carrier_ids": list(attrs.get("linked_carrier_ids") or []),
    }


def _parse_skus(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_parse_sku(item) for item in items]


def _parse_shipment(feature: dict[str, Any]) -> dict[str, Any] | None:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") not in {"Point", "LineString", "MultiPoint"}:
        return None
    props = feature.get("properties") or {}
    attrs = props.get("attributes") or {}
    return {
        "id": props.get("id") or feature.get("id"),
        "status": props.get("status"),
        "promised_delivery_utc": attrs.get("promised_delivery_utc"),
        "eta_utc": attrs.get("eta_utc"),
        "depends_on_port": attrs.get("depends_on_port"),
    }


def _parse_shipments(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        shipment
        for feature in features
        if (shipment := _parse_shipment(feature)) is not None
    ]


def _is_sku_at_risk(sku: dict[str, Any], affected_ids: set[str]) -> bool:
    if not affected_ids:
        return False
    if sku.get("id") in affected_ids:
        return True
    warehouse_id = sku.get("warehouse_id")
    if warehouse_id and warehouse_id in affected_ids:
        return True
    return any(carrier_id in affected_ids for carrier_id in sku.get("linked_carrier_ids") or [])


def _carrier_penalty_ratio(sku: dict[str, Any], affected_ids: set[str]) -> float:
    linked = sku.get("linked_carrier_ids") or []
    if not linked:
        return 1.0
    disrupted = sum(1 for carrier_id in linked if carrier_id in affected_ids)
    if disrupted <= 0:
        return 1.0
    return min(1.0, disrupted / len(linked))


def _effective_on_hand(sku: dict[str, Any], affected_ids: set[str]) -> float:
    on_hand = _float_or_zero(sku.get("on_hand_qty"))
    if not _is_sku_at_risk(sku, affected_ids):
        return on_hand
    ratio = _carrier_penalty_ratio(sku, affected_ids)
    return max(0.0, on_hand * (1 - WAREHOUSE_OR_SKU_PENALTY * ratio))


def _compute_in_stock(skus: list[dict[str, Any]], affected_ids: set[str]) -> tuple[float, str]:
    if not skus:
        return DEFAULT_KPIS["inStock"]["numeric"], "heuristic.entity_health"
    in_stock = sum(
        1
        for sku in skus
        if _effective_on_hand(sku, affected_ids) >= _float_or_zero(sku.get("safety_stock"))
    )
    return round(_ratio_percent(in_stock, len(skus))), "inventory_sku.on_hand_qty"


def _shipment_is_on_time(shipment: dict[str, Any], affected_ids: set[str]) -> bool:
    shipment_id = shipment.get("id")
    if shipment_id and shipment_id in affected_ids:
        return False
    promised = _parse_utc(shipment.get("promised_delivery_utc"))
    eta = _parse_utc(shipment.get("eta_utc"))
    return bool(promised and eta and eta <= promised)


def _on_time_from_etas(
    shipments: list[dict[str, Any]],
    affected_ids: set[str],
) -> tuple[float, str] | None:
    timed = [
        shipment
        for shipment in shipments
        if shipment.get("promised_delivery_utc") and shipment.get("eta_utc")
    ]
    if not timed:
        return None
    on_time = sum(1 for shipment in timed if _shipment_is_on_time(shipment, affected_ids))
    return round(_ratio_percent(on_time, len(timed))), "shipment_eta"


def _on_time_from_impact(impact_score: float) -> tuple[float, str] | None:
    if impact_score <= 0:
        return None
    return round(_clamp(96 - impact_score * 40, 0, 100)), "heuristic.impact_score"


def _on_time_from_health(shipments: list[dict[str, Any]]) -> tuple[float, str]:
    healthy = sum(1 for s in shipments if s.get("status") in HEALTHY_STATUSES)
    total = len(shipments) or 1
    return round(_clamp(88 + (healthy / total) * 8, 0, 100)), "heuristic.entity_health"


def _compute_on_time(
    shipments: list[dict[str, Any]],
    affected_ids: set[str],
    impact_score: float,
) -> tuple[float, str]:
    return (
        _on_time_from_etas(shipments, affected_ids)
        or _on_time_from_impact(impact_score)
        or _on_time_from_health(shipments)
    )


def _compute_turnover(skus: list[dict[str, Any]], affected_ids: set[str]) -> tuple[float, str]:
    if not skus:
        return DEFAULT_KPIS["turnover"]["numeric"], "heuristic.inventory_signal"

    annual_sales = 0.0
    inventory_value = 0.0
    for sku in skus:
        annual_sales += _float_or_zero(sku.get("avg_daily_sales_30d")) * 365
        inventory_value += _effective_on_hand(sku, affected_ids) * _float_or_zero(
            sku.get("unit_price_usd")
        )

    if inventory_value <= 0:
        return DEFAULT_KPIS["turnover"]["numeric"], "heuristic.inventory_signal"
    return _round1(_clamp(annual_sales / inventory_value, 2, 12)), "inventory_sku.avg_daily_sales_30d"


def _sku_stockout_loss(skus: list[dict[str, Any]], affected_ids: set[str]) -> float:
    loss = 0.0
    for sku in skus:
        if not _is_sku_at_risk(sku, affected_ids):
            continue
        effective = _effective_on_hand(sku, affected_ids)
        shortfall = max(0.0, _float_or_zero(sku.get("safety_stock")) - effective)
        loss += shortfall * _float_or_zero(sku.get("unit_price_usd"))
    return loss


def _pick_lost_sales(stockout_loss: float, solver_var: float) -> tuple[float, str]:
    if stockout_loss > 0 and solver_var > 0:
        return max(stockout_loss, solver_var), "max(sku_stockout,solver.var)"
    if stockout_loss > 0:
        return stockout_loss, "sku_stockout"
    if solver_var > 0:
        return solver_var, "solver.total_value_at_risk"
    return 0.0, "simulation.none"


def _compute_lost_sales(
    skus: list[dict[str, Any]],
    affected_ids: set[str],
    solver: dict[str, Any] | None,
) -> tuple[float, str]:
    stockout_loss = _sku_stockout_loss(skus, affected_ids)
    solver_var = _float_or_zero((solver or {}).get("total_value_at_risk"))
    return _pick_lost_sales(stockout_loss, solver_var)


def _reorder_from_skus(skus: list[dict[str, Any]], affected_ids: set[str]) -> tuple[float, str]:
    reorder_count = sum(
        1
        for sku in skus
        if _effective_on_hand(sku, affected_ids) <= _float_or_zero(sku.get("reorder_point"))
    )
    return round(_ratio_percent(reorder_count, len(skus))), "inventory_sku.reorder_point"


def _best_response_option(solver: dict[str, Any] | None) -> dict[str, Any] | None:
    options = (solver or {}).get("response_options") or []
    if not options:
        return None
    return next((opt for opt in options if opt.get("rank") == 1), options[0])


def _reorder_from_solver(solver: dict[str, Any] | None) -> tuple[float, str]:
    best = _best_response_option(solver)
    reduction = _float_or_zero((best or {}).get("estimated_impact_reduction"))
    if reduction:
        return round(_clamp(55 + reduction * 35, 0, 100)), "solver.response_options"

    impact_score = _float_or_zero((solver or {}).get("impact_score"))
    if impact_score:
        return round(_clamp(55 + (1 - impact_score) * 30, 0, 100)), "heuristic.impact_score"

    return DEFAULT_KPIS["reorderPoint"]["numeric"], "simulation.default"


def _compute_reorder(
    skus: list[dict[str, Any]],
    affected_ids: set[str],
    solver: dict[str, Any] | None,
) -> tuple[float, str]:
    if skus:
        return _reorder_from_skus(skus, affected_ids)
    return _reorder_from_solver(solver)


def _build_metric(
    numeric: float,
    formatter: Callable[[float], str],
    source: str,
) -> dict[str, Any]:
    return {
        "value": formatter(numeric),
        "numeric": numeric,
        "source": source,
        "confidence": "simulated",
    }


def _trend_suffix(metric_key: str) -> str:
    if metric_key == "turnover":
        return "x"
    if metric_key == "lostSales":
        return "M"
    return "%"


def _format_trend_magnitude(delta: float, suffix: str) -> str:
    if suffix == "x":
        return f"{abs(_round1(delta))}{suffix}"
    if suffix == "M":
        return f"${abs(_round1(delta))}{suffix}"
    return f"{abs(round(delta))}{suffix}"


def _format_trend_delta(current: float, baseline: float, suffix: str = "") -> dict[str, str]:
    delta = current - baseline
    if abs(delta) < 0.05:
        return {"text": "", "direction": "neutral", "sentiment": "neutral"}

    direction = "up" if delta > 0 else "down"
    arrow = "▲" if direction == "up" else "▼"
    return {
        "text": f"{arrow} {_format_trend_magnitude(delta, suffix)}",
        "direction": direction,
        "sentiment": "neutral",
    }


def _trend_sentiment(metric_key: str, direction: str) -> str:
    if direction == "neutral":
        return "neutral"
    mapping = _TREND_SENTIMENT.get(metric_key)
    if mapping:
        return mapping.get(direction, "neutral")
    # Higher inStock / onTime / turnover is better
    return "good" if direction == "up" else "bad"


def _metric_trend_values(metric_key: str, current: float, baseline: float) -> tuple[float, float]:
    if metric_key == "lostSales":
        return current / 1_000_000, baseline / 1_000_000
    return current, baseline


def _apply_trend(metric_key: str, current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    cur_val, base_val = _metric_trend_values(metric_key, current["numeric"], baseline["numeric"])
    trend = _format_trend_delta(cur_val, base_val, _trend_suffix(metric_key))
    return {
        **current,
        "trend": trend["text"],
        "trendDirection": trend["direction"],
        "trendSentiment": _trend_sentiment(metric_key, trend["direction"]),
    }


def _healthy_baseline_kpis() -> dict[str, dict[str, Any]]:
    return {
        key: {
            **metric,
            "source": "simulation.default",
            "confidence": "simulated",
            "trend": "",
            "trendDirection": "neutral",
            "trendSentiment": "neutral",
        }
        for key, metric in DEFAULT_KPIS.items()
    }


def _compute_metrics(
    skus: list[dict[str, Any]],
    shipments: list[dict[str, Any]],
    affected_ids: set[str],
    solver: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    impact_score = _float_or_zero((solver or {}).get("impact_score"))

    in_stock_num, in_stock_source = _compute_in_stock(skus, affected_ids)
    on_time_num, on_time_source = _compute_on_time(shipments, affected_ids, impact_score)
    turnover_num, turnover_source = _compute_turnover(skus, affected_ids)
    lost_sales_num, lost_sales_source = _compute_lost_sales(skus, affected_ids, solver)
    reorder_num, reorder_source = _compute_reorder(skus, affected_ids, solver)

    return {
        "inStock": _build_metric(in_stock_num, _format_percent, in_stock_source),
        "onTime": _build_metric(on_time_num, _format_percent, on_time_source),
        "turnover": _build_metric(turnover_num, _format_turnover, turnover_source),
        "lostSales": _build_metric(lost_sales_num, _format_lost_sales_millions, lost_sales_source),
        "reorderPoint": _build_metric(reorder_num, _format_percent, reorder_source),
    }


def _data_quality(
    skus: list[dict[str, Any]],
    shipments: list[dict[str, Any]],
    *,
    has_solver: bool,
    mode: str,
) -> dict[str, Any]:
    return {
        "sku_count": len(skus),
        "shipment_count": len(shipments),
        "has_solver": has_solver,
        "mode": mode,
    }


def _result_envelope(
    kpis: dict[str, dict[str, Any]],
    data_quality: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kpis": kpis,
        "data_quality": data_quality,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def compute_supply_chain_kpis(
    *,
    sku_items: list[dict[str, Any]],
    geojson_features: list[dict[str, Any]],
    solver: dict[str, Any] | None = None,
    affected_entities: list[str] | None = None,
) -> dict[str, Any]:
    skus = _parse_skus(sku_items)
    shipments = _parse_shipments(geojson_features)
    affected_ids = set(affected_entities or [])
    has_disruption = bool(solver) or bool(affected_ids)

    if not has_disruption:
        return _result_envelope(
            _healthy_baseline_kpis(),
            _data_quality(skus, shipments, has_solver=False, mode="healthy_baseline"),
        )

    current = _compute_metrics(skus, shipments, affected_ids, solver)
    kpis = {
        key: _apply_trend(key, current[key], DEFAULT_KPIS[key])
        for key in current
    }
    mode = "simulation_backed" if skus else "heuristic"
    return _result_envelope(
        kpis,
        _data_quality(skus, shipments, has_solver=bool(solver), mode=mode),
    )
