/** GeoJSON feature → entity display DTO. */

export function isFlightFeature(feature) {
  const type = feature?.properties?.type || "";
  return type === "moving_entity";
}

/** @deprecated Prefer {@link isFlightFeature}; alias for moving_entity checks. */
export const isMovingEntityFeature = isFlightFeature;

/**
 * Normalize GeoJSON feature properties for map markers / popups.
 * Used for flights and other entity kinds (name kept for compatibility).
 */
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

/** Alias with a clearer name; same shape as {@link flightInfoFromFeature}. */
export const entityInfoFromFeature = flightInfoFromFeature;
