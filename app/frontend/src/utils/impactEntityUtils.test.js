import { describe, expect, it } from "vitest";
import {
  aircraftValueUsd,
  buildValueByEntity,
  cargoCostForAircraft,
  dedupeImpactAnswer,
  diversionKey,
  diversionRoutePositions,
  resolveMapEntityId,
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
});
