/**
 * Public API for impact-simulation helpers.
 * Focused modules under `./impact/` are internal; import from this barrel.
 */

export { cargoMatchesAircraft, resolveMapEntityId } from "./impact/cargoEntityIds";
export {
  buildCompanyFilterContext,
  buildCompanyOptions,
  entityBelongsToCompany,
  filterImpactResultByCompany,
  filterMapFeaturesByCompany,
} from "./impact/companyFilter";
export { dedupeImpactAnswer } from "./impact/dedupeImpactAnswer";
export { flightInfoFromFeature, isFlightFeature } from "./impact/featureInfo";
export { formatCommodityLabel, formatCurrency } from "./impact/formatCurrency";
export {
  diversionKey,
  diversionRoutePositions,
  featureId,
  featureIdSet,
  featureLatLng,
} from "./impact/mapGeometry";
export {
  aircraftValueUsd,
  buildFlightPopupValues,
  buildValueByEntity,
  cargoCostForAircraft,
  cargoLineValue,
  skuInventoryValue,
} from "./impact/solverValues";
export { buildSupplyChainIndexes, getFlightSupplyChain } from "./impact/supplyChainIndexes";
