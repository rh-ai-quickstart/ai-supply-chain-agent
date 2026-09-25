import { cargoMatchesAircraft } from "./cargoEntityIds";
import { getFlightSupplyChain } from "./supplyChainIndexes";

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
 * Sum cargo shipment values for an aircraft from the solver breakdown.
 * Returns null when no cargo rows exist (do not substitute aircraft revenue).
 */
export function cargoCostForAircraft(aircraftId, valueByEntity, affectedIds = []) {
  let total = 0;
  let found = false;
  const ids = affectedIds.length > 0 ? affectedIds : [...valueByEntity.keys()];
  for (const id of ids) {
    if (!cargoMatchesAircraft(id, aircraftId)) continue;
    const value = valueByEntity.get(id);
    if (Number.isFinite(value)) {
      total += value;
      found = true;
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

/**
 * Pure value summary for flight map popups (breakdown preferred, else cargo index).
 */
export function buildFlightPopupValues(info, valueByEntity, affectedIds, supplyChainIndexes) {
  const { cargo, skus } = getFlightSupplyChain(info?.id, supplyChainIndexes);
  const flightValue = aircraftValueUsd(info?.id, valueByEntity, info);
  const cargoOnBoard = cargoCostForAircraft(info?.id, valueByEntity, affectedIds);

  let cargoTotalFromIndex = 0;
  let cargoIndexHasValue = false;
  for (const item of cargo) {
    const lineValue = cargoLineValue(item.attributes);
    if (Number.isFinite(lineValue)) {
      cargoTotalFromIndex += lineValue;
      cargoIndexHasValue = true;
    }
  }
  const displayCargoTotal = Number.isFinite(cargoOnBoard)
    ? cargoOnBoard
    : cargoIndexHasValue
      ? cargoTotalFromIndex
      : null;

  const totalAtRisk =
    (Number.isFinite(flightValue) ? flightValue : 0) +
    (Number.isFinite(displayCargoTotal) ? displayCargoTotal : 0);
  const showTotal =
    Number.isFinite(flightValue) && Number.isFinite(displayCargoTotal) && totalAtRisk > 0;

  return {
    cargo,
    skus,
    flightValue,
    displayCargoTotal,
    totalAtRisk,
    showTotal,
  };
}
