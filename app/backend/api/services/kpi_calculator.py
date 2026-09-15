"""Supply-chain KPI computation from simulation entity data and solver output."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

HEALTHY_STATUSES = frozenset({"airborne", "in_transit", "on_ground"})

DEFAULT_KPIS = {
    "inStock": {"value": "92%", "numeric": 92},
    "onTime": {"value": "88%", "numeric": 88},
    "turnover": {"value": "4.1x", "numeric": 4.1},
    "lostSales": {"value": "$0.0M", "numeric": 0},
    "reorderPoint": {"value": "72%", "numeric": 72},
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def _round1(value: float) -> float:
    return round(value * 10) / 10


def _format_percent(value: float) -> str:
    return f"{round(value)}%"


def _format_turnover(value: float) -> str:
    return f"{_round1(value)}x"


def _format_lost_sales_millions(amount: float) -> str:
    if amount <= 0:
        return "$0.0M"
    return f"${_round1(amount / 1_000_000)}M"


def _parse_skus(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skus: list[dict[str, Any]] = []
    for item in items:
        attrs = item.get("attributes") or {}
        skus.append(
            {
                "id": item.get("id"),
                "sku": attrs.get("sku"),
                "warehouse_id": attrs.get("warehouse_id"),
                "on_hand_qty": float(attrs.get("on_hand_qty") or 0),
                "safety_stock": float(attrs.get("safety_stock") or 0),
                "reorder_point": float(attrs.get("reorder_point") or 0),
                "unit_price_usd": float(attrs.get("unit_price_usd") or 0),
                "avg_daily_sales_30d": float(attrs.get("avg_daily_sales_30d") or 0),
                "linked_carrier_ids": list(attrs.get("linked_carrier_ids") or []),
            }
        )
    return skus


def _parse_shipments(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    shipments: list[dict[str, Any]] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"Point", "LineString", "MultiPoint"}:
            continue
        props = feature.get("properties") or {}
        attrs = props.get("attributes") or {}
        shipments.append(
            {
                "id": props.get("id") or feature.get("id"),
                "status": props.get("status"),
                "promised_delivery_utc": attrs.get("promised_delivery_utc"),
                "eta_utc": attrs.get("eta_utc"),
                "depends_on_port": attrs.get("depends_on_port"),
            }
        )
    return shipments


def _is_sku_at_risk(sku: dict[str, Any], affected_ids: set[str]) -> bool:
    if not affected_ids:
        return False
    if sku.get("id") in affected_ids:
        return True
    warehouse_id = sku.get("warehouse_id")
    if warehouse_id and warehouse_id in affected_ids:
        return True
    for carrier_id in sku.get("linked_carrier_ids") or []:
        if carrier_id in affected_ids:
            return True
    return False


def _effective_on_hand(sku: dict[str, Any], affected_ids: set[str]) -> float:
    on_hand = float(sku.get("on_hand_qty") or 0)
    if not _is_sku_at_risk(sku, affected_ids):
        return on_hand
    linked = sku.get("linked_carrier_ids") or []
    disrupted_links = sum(1 for carrier_id in linked if carrier_id in affected_ids)
    if disrupted_links == 0:
        return on_hand
    penalty_ratio = min(1.0, disrupted_links / max(1, len(linked)))
    return max(0.0, on_hand * (1 - 0.35 * penalty_ratio))


def _parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _compute_in_stock(skus: list[dict[str, Any]], affected_ids: set[str]) -> tuple[float, str]:
    if not skus:
        return DEFAULT_KPIS["inStock"]["numeric"], "heuristic.entity_health"
    in_stock = 0
    for sku in skus:
        effective = _effective_on_hand(sku, affected_ids)
        if effective >= float(sku.get("safety_stock") or 0):
            in_stock += 1
    numeric = _clamp((in_stock / len(skus)) * 100, 0, 100)
    return round(numeric), "inventory_sku.on_hand_qty"


def _compute_on_time(
    shipments: list[dict[str, Any]],
    affected_ids: set[str],
    impact_score: float,
) -> tuple[float, str]:
    timed = [
        shipment
        for shipment in shipments
        if shipment.get("promised_delivery_utc") and shipment.get("eta_utc")
    ]
    if timed:
        on_time = 0
        for shipment in timed:
            shipment_id = shipment.get("id")
            if shipment_id and shipment_id in affected_ids:
                continue
            promised = _parse_utc(shipment.get("promised_delivery_utc"))
            eta = _parse_utc(shipment.get("eta_utc"))
            if promised and eta and eta <= promised:
                on_time += 1
        numeric = _clamp((on_time / len(timed)) * 100, 0, 100)
        return round(numeric), "shipment_eta"

    if impact_score > 0:
        return round(_clamp(96 - impact_score * 40, 0, 100)), "heuristic.impact_score"

    healthy = sum(1 for s in shipments if s.get("status") in HEALTHY_STATUSES)
    total = len(shipments) or 1
    scaled = 88 + (healthy / total) * 8
    return round(_clamp(scaled, 0, 100)), "heuristic.entity_health"


def _compute_turnover(skus: list[dict[str, Any]], affected_ids: set[str]) -> tuple[float, str]:
    if not skus:
        return DEFAULT_KPIS["turnover"]["numeric"], "heuristic.inventory_signal"

    annual_sales = 0.0
    inventory_value = 0.0
    for sku in skus:
        effective = _effective_on_hand(sku, affected_ids)
        unit_price = float(sku.get("unit_price_usd") or 0)
        daily_sales = float(sku.get("avg_daily_sales_30d") or 0)
        annual_sales += daily_sales * 365
        inventory_value += effective * unit_price

    if inventory_value <= 0:
        return DEFAULT_KPIS["turnover"]["numeric"], "heuristic.inventory_signal"

    numeric = _clamp(annual_sales / inventory_value, 2, 12)
    return _round1(numeric), "inventory_sku.avg_daily_sales_30d"


def _compute_lost_sales(
    skus: list[dict[str, Any]],
    affected_ids: set[str],
    solver: dict[str, Any] | None,
) -> tuple[float, str]:
    stockout_loss = 0.0
    for sku in skus:
        if not _is_sku_at_risk(sku, affected_ids):
            continue
        effective = _effective_on_hand(sku, affected_ids)
        safety = float(sku.get("safety_stock") or 0)
        unit_price = float(sku.get("unit_price_usd") or 0)
        shortfall = max(0.0, safety - effective)
        stockout_loss += shortfall * unit_price

    solver_var = float((solver or {}).get("total_value_at_risk") or 0)
    total = stockout_loss + solver_var
    if stockout_loss > 0 and solver_var > 0:
        source = "sku_stockout+solver.var"
    elif stockout_loss > 0:
        source = "sku_stockout"
    elif solver_var > 0:
        source = "solver.total_value_at_risk"
    else:
        source = "simulation.none"
    return total, source


def _compute_reorder(skus: list[dict[str, Any]], solver: dict[str, Any] | None) -> tuple[float, str]:
    if skus:
        reorder_count = sum(
            1
            for sku in skus
            if float(sku.get("on_hand_qty") or 0) <= float(sku.get("reorder_point") or 0)
        )
        return round(_clamp((reorder_count / len(skus)) * 100, 0, 100)), "inventory_sku.reorder_point"

    options = (solver or {}).get("response_options") or []
    best = next((opt for opt in options if opt.get("rank") == 1), options[0] if options else None)
    reduction = float((best or {}).get("estimated_impact_reduction") or 0)
    if reduction:
        return round(_clamp(55 + reduction * 35, 0, 100)), "solver.response_options"

    impact_score = float((solver or {}).get("impact_score") or 0)
    if impact_score:
        return round(_clamp(55 + (1 - impact_score) * 30, 0, 100)), "heuristic.impact_score"

    return DEFAULT_KPIS["reorderPoint"]["numeric"], "simulation.default"


def _build_metric(
    numeric: float,
    formatter,
    source: str,
) -> dict[str, Any]:
    return {
        "value": formatter(numeric),
        "numeric": numeric,
        "source": source,
        "confidence": "simulated",
    }


def _format_trend_delta(current: float, baseline: float, suffix: str = "") -> dict[str, str]:
    delta = current - baseline
    if abs(delta) < 0.05:
        return {"text": "", "direction": "neutral", "sentiment": "neutral"}

    direction = "up" if delta > 0 else "down"
    if suffix == "x":
        magnitude = f"{abs(_round1(delta))}{suffix}"
    elif suffix == "M":
        magnitude = f"${abs(_round1(delta))}{suffix}"
    else:
        magnitude = f"{abs(round(delta))}{suffix}"

    return {
        "text": f"{'▲' if direction == 'up' else '▼'} {magnitude}",
        "direction": direction,
        "sentiment": "neutral",
    }


def _apply_trend(metric_key: str, current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    if metric_key == "lostSales":
        trend = _format_trend_delta(
            current["numeric"] / 1_000_000,
            baseline["numeric"] / 1_000_000,
            "M",
        )
        sentiment = "bad" if trend["direction"] == "up" else "good" if trend["direction"] == "down" else "neutral"
    elif metric_key == "reorderPoint":
        trend = _format_trend_delta(current["numeric"], baseline["numeric"], "%")
        sentiment = (
            "caution"
            if trend["direction"] == "up"
            else "good"
            if trend["direction"] == "down"
            else "neutral"
        )
    else:
        suffix = "x" if metric_key == "turnover" else "%"
        trend = _format_trend_delta(current["numeric"], baseline["numeric"], suffix)
        sentiment = (
            "bad"
            if trend["direction"] == "down"
            else "good"
            if trend["direction"] == "up"
            else "neutral"
        )

    return {
        **current,
        "trend": trend["text"],
        "trendDirection": trend["direction"],
        "trendSentiment": sentiment,
    }


def _compute_metrics(
    skus: list[dict[str, Any]],
    shipments: list[dict[str, Any]],
    affected_ids: set[str],
    solver: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    impact_score = float((solver or {}).get("impact_score") or 0)

    in_stock_num, in_stock_source = _compute_in_stock(skus, affected_ids)
    on_time_num, on_time_source = _compute_on_time(shipments, affected_ids, impact_score)
    turnover_num, turnover_source = _compute_turnover(skus, affected_ids)
    lost_sales_num, lost_sales_source = _compute_lost_sales(skus, affected_ids, solver)
    reorder_num, reorder_source = _compute_reorder(skus, solver)

    return {
        "inStock": _build_metric(in_stock_num, _format_percent, in_stock_source),
        "onTime": _build_metric(on_time_num, _format_percent, on_time_source),
        "turnover": _build_metric(turnover_num, _format_turnover, turnover_source),
        "lostSales": _build_metric(lost_sales_num, _format_lost_sales_millions, lost_sales_source),
        "reorderPoint": _build_metric(reorder_num, _format_percent, reorder_source),
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

    if not skus and not shipments and not solver:
        kpis = {
            key: {**metric, "trend": "", "trendDirection": "neutral", "trendSentiment": "neutral"}
            for key, metric in {
                "inStock": {**DEFAULT_KPIS["inStock"], "source": "simulation.default", "confidence": "simulated"},
                "onTime": {**DEFAULT_KPIS["onTime"], "source": "simulation.default", "confidence": "simulated"},
                "turnover": {**DEFAULT_KPIS["turnover"], "source": "simulation.default", "confidence": "simulated"},
                "lostSales": {**DEFAULT_KPIS["lostSales"], "source": "simulation.default", "confidence": "simulated"},
                "reorderPoint": {**DEFAULT_KPIS["reorderPoint"], "source": "simulation.default", "confidence": "simulated"},
            }.items()
        }
        return {
            "kpis": kpis,
            "data_quality": {
                "sku_count": 0,
                "shipment_count": 0,
                "has_solver": False,
                "mode": "default",
            },
        }

    baseline = _compute_metrics(skus, shipments, set(), None)
    current = _compute_metrics(skus, shipments, affected_ids, solver)

    kpis = {
        key: _apply_trend(key, current[key], baseline[key])
        for key in current
    }

    mode = "simulation_backed" if skus else "heuristic"
    return {
        "kpis": kpis,
        "data_quality": {
            "sku_count": len(skus),
            "shipment_count": len(shipments),
            "has_solver": bool(solver),
            "mode": mode,
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
