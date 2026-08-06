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

export function flightInfoFromFeature(feature) {
  const props = feature?.properties || {};
  const attrs = props.attributes && typeof props.attributes === "object" ? props.attributes : {};
  return {
    id: props.id ?? feature?.id ?? "",
    type: props.type || "",
    status: props.status || "",
    callSign: attrs.call_sign || attrs.callsign || "",
    route: attrs.route || "",
    originCountry: attrs.origin_country || "",
    revenueUsd: Number.isFinite(Number(attrs.revenue_usd)) ? Number(attrs.revenue_usd) : null,
    valueUsd: Number.isFinite(Number(attrs.value_usd)) ? Number(attrs.value_usd) : null,
  };
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
