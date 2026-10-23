import { cargoMatchesAircraft } from "./cargoEntityIds";
import { flightInfoFromFeature, isFlightFeature } from "./featureInfo";

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
 * @param {{ cargoByCarrier?: Map, skusByCarrier?: Map } | null} supplyChainIndexes
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
    for (const flightId of context.flightIdsByCompany.get(companyId) || []) {
      if (cargoMatchesAircraft(entityId, flightId)) return true;
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
