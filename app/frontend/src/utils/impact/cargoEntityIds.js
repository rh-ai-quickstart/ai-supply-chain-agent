/**
 * Cargo IDs are typically `cargo-{aircraftId}` or `cargo-{aircraftId}-{n}`.
 * Shared matching so map focus, company filter, and value sums stay consistent.
 */

/** True when `cargoId` is cargo carried by `aircraftId`. */
export function cargoMatchesAircraft(cargoId, aircraftId) {
  if (!cargoId || !aircraftId || !cargoId.startsWith("cargo-")) return false;
  return cargoId === `cargo-${aircraftId}` || cargoId.startsWith(`cargo-${aircraftId}-`);
}

/**
 * Cargo IDs often lack geometry. Prefer the mapped aircraft marker when the
 * cargo itself is not on the map.
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
