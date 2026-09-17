/** Helpers for linking impact results to map markers. */

export function formatCurrency(amount, currency = "USD") {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return `${currency} —`;
  }
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  }
}

export function buildValueByEntity(breakdown) {
  const map = new Map();
  if (!Array.isArray(breakdown)) return map;
  for (const row of breakdown) {
    if (!row?.entity_id) continue;
    const value = Number(row.value_usd);
    if (Number.isFinite(value)) {
      map.set(row.entity_id, value);
    }
  }
  return map;
}

/**
 * Cargo IDs are typically `cargo-{aircraftId}-{n}` and often lack geometry.
 * Prefer the mapped aircraft marker when the cargo itself is not on the map.
 */
export function resolveMapEntityId(entityId, featureIdSet) {
  if (!entityId) return "";
  if (featureIdSet.has(entityId)) return entityId;

  const match = /^cargo-(.+)-(\d+)$/.exec(entityId);
  if (match && featureIdSet.has(match[1])) {
    return match[1];
  }

  if (entityId.startsWith("cargo-")) {
    const rest = entityId.slice("cargo-".length);
    let best = "";
    for (const featureId of featureIdSet) {
      if (rest === featureId || rest.startsWith(`${featureId}-`)) {
        if (featureId.length > best.length) best = featureId;
      }
    }
    if (best) return best;
  }

  return entityId;
}

/**
 * Sum cargo shipment values for an aircraft from the solver breakdown.
 * Cargo IDs are `cargo-{aircraftId}` or `cargo-{aircraftId}-{n}`.
 * Returns null when no cargo rows exist (do not substitute aircraft revenue).
 */
export function cargoCostForAircraft(aircraftId, valueByEntity, affectedIds = []) {
  let total = 0;
  let found = false;
  const ids = affectedIds.length > 0 ? affectedIds : [...valueByEntity.keys()];
  for (const id of ids) {
    if (!id.startsWith("cargo-")) continue;
    if (id === `cargo-${aircraftId}` || id.startsWith(`cargo-${aircraftId}-`)) {
      const value = valueByEntity.get(id);
      if (Number.isFinite(value)) {
        total += value;
        found = true;
      }
    }
  }
  return found ? total : null;
}

/** Aircraft economic value from breakdown, else live revenue/value attributes. */
export function aircraftValueUsd(aircraftId, valueByEntity, flightInfo) {
  const fromBreakdown = valueByEntity.get(aircraftId);
  if (Number.isFinite(fromBreakdown)) return fromBreakdown;
  if (Number.isFinite(flightInfo?.revenueUsd)) return flightInfo.revenueUsd;
  if (Number.isFinite(flightInfo?.valueUsd)) return flightInfo.valueUsd;
  return null;
}

export function isFlightFeature(feature) {
  const type = feature?.properties?.type || "";
  return type === "moving_entity";
}

/** Unique company options from flight features that declare `company_id`. */
export function buildCompanyOptions(features = []) {
  const byId = new Map();
  for (const feature of features) {
    if (!isFlightFeature(feature)) continue;
    const info = flightInfoFromFeature(feature);
    if (!info.companyId) continue;
    if (!byId.has(info.companyId)) {
      byId.set(info.companyId, info.companyName || info.companyId);
    } else if (info.companyName) {
      byId.set(info.companyId, info.companyName);
    }
  }
  return [...byId.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

/**
 * Lookup tables for filtering map features and scenario results by company.
 * @param {object[]} features GeoJSON features
 * @param {ReturnType<typeof buildSupplyChainIndexes>} supplyChainIndexes
 */
export function buildCompanyFilterContext(features = [], supplyChainIndexes = null) {
  const flightIdsByCompany = new Map();
  const flightCompanyById = new Map();
  const entityIdsByCompany = new Map();

  for (const feature of features) {
    if (!isFlightFeature(feature)) continue;
    const info = flightInfoFromFeature(feature);
    if (!info.id || !info.companyId) continue;
    flightCompanyById.set(info.id, info.companyId);
    if (!flightIdsByCompany.has(info.companyId)) {
      flightIdsByCompany.set(info.companyId, new Set());
    }
    flightIdsByCompany.get(info.companyId).add(info.id);
  }

  const cargoByCarrier = supplyChainIndexes?.cargoByCarrier || new Map();
  const skusByCarrier = supplyChainIndexes?.skusByCarrier || new Map();

  for (const [companyId, flightIds] of flightIdsByCompany) {
    const entityIds = new Set(flightIds);
    for (const flightId of flightIds) {
      for (const item of cargoByCarrier.get(flightId) || []) {
        if (item?.id) entityIds.add(item.id);
      }
      for (const item of skusByCarrier.get(flightId) || []) {
        if (item?.id) entityIds.add(item.id);
      }
    }
    entityIdsByCompany.set(companyId, entityIds);
  }

  return { flightIdsByCompany, flightCompanyById, entityIdsByCompany };
}

export function entityBelongsToCompany(entityId, companyId, context) {
  if (!companyId || !entityId) return true;
  const allowed = context?.entityIdsByCompany?.get(companyId);
  if (!allowed) return false;
  if (allowed.has(entityId)) return true;

  if (entityId.startsWith("cargo-")) {
    const rest = entityId.slice("cargo-".length);
    for (const flightId of context.flightIdsByCompany.get(companyId) || []) {
      if (rest === flightId || rest.startsWith(`${flightId}-`)) return true;
    }
  }

  return false;
}

/** Hide flights that do not match the selected company; keep other entity kinds visible. */
export function filterMapFeaturesByCompany(features = [], companyId = "") {
  if (!companyId) return features;
  return features.filter((feature) => {
    if (!isFlightFeature(feature)) return true;
    return flightInfoFromFeature(feature).companyId === companyId;
  });
}

/** Narrow scenario impact results to entities tied to the selected company. */
export function filterImpactResultByCompany(result, companyId = "", context = null) {
  if (!result || !companyId || !context) return result;

  const belongs = (entityId) => entityBelongsToCompany(entityId, companyId, context);
  const affected = (Array.isArray(result.affected_entities) ? result.affected_entities : []).filter(
    belongs,
  );
  const solver = result.solver && typeof result.solver === "object" ? result.solver : {};
  const breakdown = (Array.isArray(solver.value_breakdown) ? solver.value_breakdown : []).filter(
    (row) => belongs(row?.entity_id),
  );
  const reroutes = (Array.isArray(solver.recommended_reroutes) ? solver.recommended_reroutes : []).filter(
    (row) => belongs(row?.entity_id),
  );
  const totalValue = breakdown.reduce((sum, row) => {
    const value = Number(row?.value_usd);
    return Number.isFinite(value) ? sum + value : sum;
  }, 0);

  return {
    ...result,
    affected_entities: affected,
    solver: {
      ...solver,
      value_breakdown: breakdown,
      recommended_reroutes: reroutes,
      affected_count: affected.length,
      total_value_at_risk: breakdown.length > 0 ? totalValue : solver.total_value_at_risk,
    },
  };
}

export function flightInfoFromFeature(feature) {
  const props = feature?.properties || {};
  const attrs = props.attributes && typeof props.attributes === "object" ? props.attributes : {};
  return {
    id: props.id ?? feature?.id ?? "",
    type: props.type || "",
    status: props.status || "",
    callSign: attrs.call_sign || attrs.callsign || "",
    route: attrs.route || "",
    originCountry: attrs.origin_country || attrs.origin || "",
    companyId: attrs.company_id || "",
    companyName: attrs.company_name || "",
    revenueUsd: Number.isFinite(Number(attrs.revenue_usd)) ? Number(attrs.revenue_usd) : null,
    valueUsd: Number.isFinite(Number(attrs.value_usd)) ? Number(attrs.value_usd) : null,
  };
}

/**
 * Index cargo and SKU entities by carrier flight id for map popups.
 * @param {Array<{ id: string, type: string, attributes?: object }>} entities
 */
export function buildSupplyChainIndexes(entities = []) {
  const cargoByCarrier = new Map();
  const skusByCarrier = new Map();

  for (const item of entities) {
    if (!item?.id) continue;
    const attrs = item.attributes && typeof item.attributes === "object" ? item.attributes : {};

    if (item.type === "cargo_item") {
      const carrierId = attrs.carrier_id;
      if (!carrierId) continue;
      if (!cargoByCarrier.has(carrierId)) cargoByCarrier.set(carrierId, []);
      cargoByCarrier.get(carrierId).push(item);
      continue;
    }

    if (item.type === "inventory_sku") {
      const linked = Array.isArray(attrs.linked_carrier_ids) ? attrs.linked_carrier_ids : [];
      for (const carrierId of linked) {
        if (!carrierId) continue;
        if (!skusByCarrier.has(carrierId)) skusByCarrier.set(carrierId, []);
        skusByCarrier.get(carrierId).push(item);
      }
    }
  }

  return { cargoByCarrier, skusByCarrier };
}

export function getFlightSupplyChain(flightId, indexes) {
  if (!flightId || !indexes) {
    return { cargo: [], skus: [] };
  }
  return {
    cargo: indexes.cargoByCarrier?.get(flightId) || [],
    skus: indexes.skusByCarrier?.get(flightId) || [],
  };
}

export function cargoLineValue(attrs = {}) {
  const explicit = Number(attrs.value_usd);
  if (Number.isFinite(explicit)) return explicit;
  const qty = Number(attrs.quantity);
  const unit = Number(attrs.unit_price_usd);
  if (Number.isFinite(qty) && Number.isFinite(unit)) return qty * unit;
  return null;
}

export function skuInventoryValue(attrs = {}) {
  const explicit = Number(attrs.value_usd);
  if (Number.isFinite(explicit)) return explicit;
  const qty = Number(attrs.on_hand_qty ?? attrs.quantity);
  const unit = Number(attrs.unit_price_usd);
  if (Number.isFinite(qty) && Number.isFinite(unit)) return qty * unit;
  return null;
}

export function formatCommodityLabel(value) {
  if (!value) return "—";
  return String(value).replace(/_/g, " ");
}

/** Stable key for a recommended diversion / reroute row. */
export function diversionKey(route) {
  if (!route) return "";
  return `${route.entity_id || ""}|${route.target_id || ""}`;
}

/**
 * Markdown section headings that duplicate structured Impact Results panels.
 * Matched case-insensitively against ATX (#) headings and plain title lines.
 */
const DUPLICATE_ANSWER_SECTIONS = {
  diversions: [
    /^#{1,6}\s*recommended\s+diversions?\b.*$/i,
    /^#{1,6}\s*recommended\s+reroutes?\b.*$/i,
    /^recommended\s+diversions?\s*$/i,
    /^recommended\s+reroutes?\s*$/i,
  ],
  options: [
    /^#{1,6}\s*summary\s+of\s+action\s+items?\b.*$/i,
    /^#{1,6}\s*response\s+options?\b.*$/i,
    /^#{1,6}\s*action\s+items?\b.*$/i,
    /^summary\s+of\s+action\s+items?\s*$/i,
    /^response\s+options?\s*$/i,
    /^action\s+items?\s*$/i,
  ],
  cost: [
    /^#{1,6}\s*estimated\s+cost(?:\s+of\s+impact)?\b.*$/i,
    /^#{1,6}\s*value\s+at\s+risk\b.*$/i,
    /^estimated\s+cost(?:\s+of\s+impact)?\s*$/i,
    /^value\s+at\s+risk\s*$/i,
  ],
};

function isSectionHeading(line) {
  const trimmed = line.trim();
  if (!trimmed) return false;
  if (/^#{1,6}\s+\S/.test(trimmed)) return true;
  // Plain title: a few Title-Case / word tokens, no sentence punctuation.
  return /^[A-Z][A-Za-z0-9/()-]*(?:\s+[A-Za-z0-9/()-]+){0,6}$/.test(trimmed);
}

/**
 * Drop prose answer sections that the sidebar already renders as structured UI
 * (interactive diversions, response options, KPI value-at-risk).
 */
export function dedupeImpactAnswer(
  answer,
  { hasReroutes = false, hasOptions = false, hasValueAtRisk = false } = {},
) {
  if (!answer || typeof answer !== "string") return answer || "";

  const patterns = [];
  if (hasReroutes) patterns.push(...DUPLICATE_ANSWER_SECTIONS.diversions);
  if (hasOptions) patterns.push(...DUPLICATE_ANSWER_SECTIONS.options);
  if (hasValueAtRisk) patterns.push(...DUPLICATE_ANSWER_SECTIONS.cost);
  if (patterns.length === 0) return answer.trim();

  const kept = [];
  let skipping = false;

  for (const line of answer.split("\n")) {
    const trimmed = line.trim();
    const matchesDrop = patterns.some((re) => re.test(trimmed));

    if (skipping) {
      if (isSectionHeading(line) && !matchesDrop) {
        skipping = false;
        kept.push(line);
      }
      continue;
    }

    if (matchesDrop) {
      skipping = true;
      continue;
    }
    kept.push(line);
  }

  return kept
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/**
 * Lat/lng pair for a map feature Point geometry.
 * Returns null when geometry is missing or invalid.
 */
export function featureLatLng(feature) {
  const geometry = feature?.geometry;
  if (!geometry || geometry.type !== "Point" || !Array.isArray(geometry.coordinates)) {
    return null;
  }
  const [lon, lat] = geometry.coordinates;
  if (typeof lon !== "number" || typeof lat !== "number") {
    return null;
  }
  return [lat, lon];
}

/**
 * Build aircraft → diversion-airport positions for a selected reroute.
 * Returns null when either endpoint cannot be resolved.
 */
export function diversionRoutePositions(route, features = []) {
  if (!route || typeof route.latitude !== "number" || typeof route.longitude !== "number") {
    return null;
  }
  const featureIds = new Set(
    features.map((feature) => feature.properties?.id ?? feature.id).filter(Boolean),
  );
  const mapId = resolveMapEntityId(route.entity_id, featureIds);
  const feature = features.find((item) => (item.properties?.id ?? item.id) === mapId);
  const from = featureLatLng(feature);
  if (!from) return null;
  return [from, [route.latitude, route.longitude]];
}
