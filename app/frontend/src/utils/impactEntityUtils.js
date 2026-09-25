/**
 * Barrel re-exports for impact-simulation helpers.
 * Prefer importing from focused modules under `./impact/` in new code.
 */

export { formatCurrency, formatCommodityLabel } from "./impact/formatCurrency";
export { cargoMatchesAircraft, resolveMapEntityId } from "./impact/cargoEntityIds";
export {
  buildValueByEntity,
  cargoCostForAircraft,
  aircraftValueUsd,
  cargoLineValue,
  skuInventoryValue,
  buildFlightPopupValues,
} from "./impact/solverValues";
export {
  buildCompanyOptions,
  buildCompanyFilterContext,
  entityBelongsToCompany,
  filterMapFeaturesByCompany,
  filterImpactResultByCompany,
} from "./impact/companyFilter";
export {
  isFlightFeature,
  isMovingEntityFeature,
  flightInfoFromFeature,
  entityInfoFromFeature,
} from "./impact/featureInfo";
export { buildSupplyChainIndexes, getFlightSupplyChain } from "./impact/supplyChainIndexes";
export { diversionKey, featureLatLng, diversionRoutePositions } from "./impact/mapGeometry";
export { dedupeImpactAnswer } from "./impact/dedupeImpactAnswer";
