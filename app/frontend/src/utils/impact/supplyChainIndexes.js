/**
 * Index cargo and SKU entities by carrier flight id for map popups.
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
