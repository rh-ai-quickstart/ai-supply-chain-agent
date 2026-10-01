import { describe, expect, it } from "vitest";
import {
  aircraftValueUsd,
  buildCompanyFilterContext,
  buildCompanyOptions,
  buildSupplyChainIndexes,
  buildValueByEntity,
  cargoCostForAircraft,
  cargoLineValue,
  dedupeImpactAnswer,
  diversionKey,
  diversionRoutePositions,
  entityBelongsToCompany,
  filterImpactResultByCompany,
  filterMapFeaturesByCompany,
  flightInfoFromFeature,
  getFlightSupplyChain,
  resolveMapEntityId,
  skuInventoryValue,
} from "./impactEntityUtils";

describe("impactEntityUtils", () => {
  it("builds a value map from solver breakdown", () => {
    const map = buildValueByEntity([
      { entity_id: "opensky-1", value_usd: 100 },
      { entity_id: "cargo-opensky-1-1", value_usd: 50 },
    ]);
    expect(map.get("opensky-1")).toBe(100);
    expect(map.get("cargo-opensky-1-1")).toBe(50);
  });

  it("resolves cargo ids to parent aircraft markers when needed", () => {
    const ids = new Set(["opensky-407290", "opensky-471f52"]);
    expect(resolveMapEntityId("opensky-407290", ids)).toBe("opensky-407290");
    expect(resolveMapEntityId("cargo-opensky-407290-1", ids)).toBe("opensky-407290");
  });

  it("sums cargo cost for an aircraft from breakdown rows only", () => {
    const values = buildValueByEntity([
      { entity_id: "opensky-407290", value_usd: 620000 },
      { entity_id: "cargo-opensky-407290-1", value_usd: 102000 },
      { entity_id: "cargo-opensky-407290-2", value_usd: 48000 },
      { entity_id: "cargo-opensky-other-1", value_usd: 10 },
    ]);
    expect(
      cargoCostForAircraft(
        "opensky-407290",
        values,
        [
          "opensky-407290",
          "cargo-opensky-407290-1",
          "cargo-opensky-407290-2",
          "cargo-opensky-other-1",
        ],
      ),
    ).toBe(150000);
  });

  it("does not treat aircraft revenue as cargo when no cargo rows exist", () => {
    const values = buildValueByEntity([{ entity_id: "opensky-407290", value_usd: 620000 }]);
    expect(cargoCostForAircraft("opensky-407290", values, ["opensky-407290"])).toBeNull();
    expect(aircraftValueUsd("opensky-407290", values, { revenueUsd: 620000 })).toBe(620000);
  });

  it("builds diversion keys and route positions from aircraft to alternate", () => {
    const route = {
      entity_id: "opensky-407290",
      target_id: "EIDW",
      latitude: 53.4213,
      longitude: -6.2701,
    };
    expect(diversionKey(route)).toBe("opensky-407290|EIDW");
    expect(
      diversionRoutePositions(route, [
        {
          type: "Feature",
          properties: { id: "opensky-407290" },
          geometry: { type: "Point", coordinates: [-0.1, 51.5] },
        },
      ]),
    ).toEqual([
      [51.5, -0.1],
      [53.4213, -6.2701],
    ]);
  });

  it("strips answer sections that duplicate structured sidebar panels", () => {
    const answer = [
      "Affected Aircraft",
      "EZY8742 - Route: LGW-FCO",
      "",
      "Recommended Diversions",
      "EZY8742 (LGW-FCO) → Paris CDG (LFPG)",
      "",
      "Estimated Cost of Impact",
      "The Total Value at Risk is USD 3,854,900.",
      "",
      "Summary of Action Items",
      "Divert listed flights immediately.",
    ].join("\n");

    const cleaned = dedupeImpactAnswer(answer, {
      hasReroutes: true,
      hasOptions: true,
      hasValueAtRisk: true,
    });

    expect(cleaned).toContain("Affected Aircraft");
    expect(cleaned).toContain("EZY8742 - Route: LGW-FCO");
    expect(cleaned).not.toContain("Recommended Diversions");
    expect(cleaned).not.toContain("Paris CDG");
    expect(cleaned).not.toContain("Estimated Cost");
    expect(cleaned).not.toContain("3,854,900");
    expect(cleaned).not.toContain("Summary of Action Items");
  });

  it("keeps diversion prose when no structured reroutes are present", () => {
    const answer = "Recommended Diversions\nEZY8742 → Paris CDG";
    expect(dedupeImpactAnswer(answer, { hasReroutes: false })).toContain("Paris CDG");
  });

  it("indexes cargo and SKUs by carrier flight id", () => {
    const indexes = buildSupplyChainIndexes([
      {
        id: "cargo-1",
        type: "cargo_item",
        attributes: { carrier_id: "flight-a", commodity: "pharma", quantity: 2, unit_price_usd: 100 },
      },
      {
        id: "sku-1",
        type: "inventory_sku",
        attributes: { sku: "SKU-1", linked_carrier_ids: ["flight-a"], on_hand_qty: 5, unit_price_usd: 50 },
      },
    ]);
    const chain = getFlightSupplyChain("flight-a", indexes);
    expect(chain.cargo).toHaveLength(1);
    expect(chain.skus).toHaveLength(1);
    expect(cargoLineValue(chain.cargo[0].attributes)).toBe(200);
    expect(skuInventoryValue(chain.skus[0].attributes)).toBe(250);
  });

  it("reads company_id from flight feature attributes", () => {
    const info = flightInfoFromFeature({
      properties: {
        id: "flight-a",
        type: "moving_entity",
        attributes: { call_sign: "BAW1", company_id: "company-1", company_name: "Acme Air" },
      },
    });
    expect(info.companyId).toBe("company-1");
    expect(info.companyName).toBe("Acme Air");
  });

  it("builds company options and filters map features by company", () => {
    const features = [
      {
        type: "Feature",
        properties: {
          id: "flight-a",
          type: "moving_entity",
          attributes: { company_id: "company-1", company_name: "Acme Air" },
        },
      },
      {
        type: "Feature",
        properties: {
          id: "flight-b",
          type: "moving_entity",
          attributes: { company_id: "company-2", company_name: "Beta Freight" },
        },
      },
      {
        type: "Feature",
        properties: { id: "PORT001", type: "facility" },
      },
    ];
    expect(buildCompanyOptions(features)).toEqual([
      { id: "company-1", label: "Acme Air" },
      { id: "company-2", label: "Beta Freight" },
    ]);
    const filtered = filterMapFeaturesByCompany(features, "company-1");
    expect(filtered.map((feature) => feature.properties.id)).toEqual(["flight-a", "PORT001"]);
  });

  it("filters scenario results to the selected company flights and cargo", () => {
    const features = [
      {
        type: "Feature",
        properties: {
          id: "flight-a",
          type: "moving_entity",
          attributes: { company_id: "company-1" },
        },
      },
      {
        type: "Feature",
        properties: {
          id: "flight-b",
          type: "moving_entity",
          attributes: { company_id: "company-2" },
        },
      },
    ];
    const indexes = buildSupplyChainIndexes([
      {
        id: "cargo-flight-a-1",
        type: "cargo_item",
        attributes: { carrier_id: "flight-a", value_usd: 100 },
      },
    ]);
    const context = buildCompanyFilterContext(features, indexes);
    expect(entityBelongsToCompany("flight-a", "company-1", context)).toBe(true);
    expect(entityBelongsToCompany("cargo-flight-a-1", "company-1", context)).toBe(true);
    expect(entityBelongsToCompany("flight-b", "company-1", context)).toBe(false);

    const filtered = filterImpactResultByCompany(
      {
        affected_entities: ["flight-a", "flight-b", "cargo-flight-a-1"],
        solver: {
          value_breakdown: [
            { entity_id: "flight-a", value_usd: 50 },
            { entity_id: "flight-b", value_usd: 200 },
            { entity_id: "cargo-flight-a-1", value_usd: 100 },
          ],
          recommended_reroutes: [
            { entity_id: "flight-a", target_id: "EIDW" },
            { entity_id: "flight-b", target_id: "LFPG" },
          ],
        },
      },
      "company-1",
      context,
    );
    expect(filtered.affected_entities).toEqual(["flight-a", "cargo-flight-a-1"]);
    expect(filtered.solver.value_breakdown).toHaveLength(2);
    expect(filtered.solver.recommended_reroutes).toEqual([
      { entity_id: "flight-a", target_id: "EIDW" },
    ]);
    expect(filtered.solver.total_value_at_risk).toBe(150);
    expect(filtered.solver.affected_count).toBe(2);
  });
});
