import { describe, expect, it } from "vitest";
import {
  aircraftValueUsd,
  buildValueByEntity,
  cargoCostForAircraft,
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
});
