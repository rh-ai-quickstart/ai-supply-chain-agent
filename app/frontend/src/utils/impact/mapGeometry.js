import { resolveMapEntityId } from "./cargoEntityIds";

/** Stable key for a recommended diversion / reroute row. */
export function diversionKey(route) {
  if (!route) return "";
  return `${route.entity_id || ""}|${route.target_id || ""}`;
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
