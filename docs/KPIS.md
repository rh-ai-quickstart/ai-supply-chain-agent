# Supply-chain KPIs

How the impact workspace KPI bar is computed.

| Layer | Location |
|-------|----------|
| Formulas | [`app/backend/api/services/kpi_calculator.py`](../app/backend/api/services/kpi_calculator.py) |
| API | `GET /api/v1/kpis` via [`KpiService`](../app/backend/api/services/kpi_service.py) |
| UI labels / tooltips | [`app/frontend/src/utils/supplyChainKpis.js`](../app/frontend/src/utils/supplyChainKpis.js) |

KPIs are **simulated** from seeded inventory SKUs, shipment GeoJSON, and optional solver impact output. They are not live ERP metrics.

---

## Modes

| Mode | When | Behavior |
|------|------|----------|
| `healthy_baseline` | No solver payload and no `affected_entities` | Fixed defaults (100% in-stock / on-time, 6.5x turnover, $0 lost sales, 0% reorder). Trends empty. |
| `simulation_backed` | Disruption present **and** SKUs loaded | Metrics from inventory + shipments (+ solver when provided). Trends vs healthy defaults. |
| `heuristic` | Disruption present **but** no SKUs | On-time / reorder fall back to solver or shipment health heuristics. |

Disruption is present when either `solver` is non-empty or `affected_entities` is non-empty.

---

## Shared inventory model

Several metrics use **effective on-hand** after disruption:

1. A SKU is **at risk** if its id, `warehouse_id`, or any `linked_carrier_ids` entry is in `affected_entities`.
2. Effective on-hand = `on_hand_qty × (1 − 0.35 × penalty_ratio)`.
3. `penalty_ratio`:
   - `1.0` when the warehouse/SKU is hit with no linked-carrier hits (or no carriers linked)
   - otherwise `disrupted_carriers / linked_carriers` (capped at 1)

Constant: `WAREHOUSE_OR_SKU_PENALTY = 0.35`.

---

## Metrics

### In-Stock Rate (`inStock`)

| | |
|--|--|
| **Meaning** | Share of SKUs whose effective on-hand is at or above safety stock |
| **Display** | Percent |
| **Formula** | `round(100 × count(effective ≥ safety_stock) / sku_count)` |
| **Primary source** | `inventory_sku.on_hand_qty` |
| **Fallback** | Healthy default when no SKUs |
| **Trend** | Up = good, down = bad |

### On-Time Delivery (`onTime`)

| | |
|--|--|
| **Meaning** | Share of timed shipments arriving by promised delivery |
| **Display** | Percent |
| **Priority** | 1) ETA pair → 2) solver `impact_score` → 3) shipment status health |

1. **Shipment ETA** (`shipment_eta`): among shipments with both `promised_delivery_utc` and `eta_utc`, count those with `eta ≤ promised` and id not in `affected_entities`.
2. **Impact heuristic** (`heuristic.impact_score`): `clamp(96 − impact_score × 40, 0, 100)` when `impact_score > 0`.
3. **Entity health** (`heuristic.entity_health`): `clamp(88 + 8 × healthy/total, 0, 100)` where healthy statuses are `airborne`, `in_transit`, `on_ground`.

**Trend:** up = good, down = bad.

### Inventory Turnover (`turnover`)

| | |
|--|--|
| **Meaning** | Annualized sales velocity vs effective inventory value |
| **Display** | Multiplier (`x`) |
| **Formula** | `clamp(Σ(avg_daily_sales_30d × 365) / Σ(effective_on_hand × unit_price_usd), 2, 12)` |
| **Primary source** | `inventory_sku.avg_daily_sales_30d` |
| **Fallback** | `6.5x` when no SKUs or zero inventory value |
| **Trend** | Up = good, down = bad |

### Lost Sales (`lostSales`)

| | |
|--|--|
| **Meaning** | Stockout exposure under disruption (USD), shown in millions |
| **Display** | `$X.YM` |
| **SKU stockout** | For at-risk SKUs: `Σ max(0, safety_stock − effective_on_hand) × unit_price_usd` |
| **Solver VaR** | `solver.total_value_at_risk` when present |
| **Combine** | If both &gt; 0 → `max(stockout, VaR)` (not sum); else whichever is &gt; 0 |

**Trend:** up = bad, down = good (compared in millions vs $0 baseline).

### Optimal Reorder (`reorderPoint`)

| | |
|--|--|
| **Meaning** | Share of SKUs at or below reorder point (using effective on-hand) |
| **Display** | Percent |
| **With SKUs** | `round(100 × count(effective ≤ reorder_point) / sku_count)` |
| **Without SKUs** | Rank-1 `response_options.estimated_impact_reduction` → `55 + reduction × 35`; else `55 + (1 − impact_score) × 30`; else `0%` |
| **Trend** | Up = caution, down = good |

---

## Response shape

Each metric in `kpis` includes:

| Field | Purpose |
|-------|---------|
| `value` | Display string |
| `numeric` | Raw number used for trends |
| `source` | Which formula path produced the value |
| `confidence` | Always `simulated` today |
| `trend` | Arrow + magnitude vs healthy default (empty when unchanged) |
| `trendDirection` | `up` / `down` / `neutral` |
| `trendSentiment` | `good` / `bad` / `caution` / `neutral` |

`data_quality` reports `sku_count`, `shipment_count`, `has_solver`, and `mode`.

---

## Seeding inputs

Populate SKUs and carriers via network overlay YAML (`make seed-network-overlay`). Relevant fields:

- `inventory_skus`: `on_hand_qty`, `safety_stock`, `reorder_point`, `unit_price_usd`, `avg_daily_sales_30d`, `warehouse_id`, `linked_carrier_ids`
- Flights/vessels + cargo: carriers that appear in `affected_entities` and SKU links
- Optional shipment ETAs on moving entities: `promised_delivery_utc`, `eta_utc`

See [`data/supply-chain-network.example.yaml`](../data/supply-chain-network.example.yaml).
