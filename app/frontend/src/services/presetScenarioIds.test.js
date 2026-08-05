import { describe, expect, it } from "vitest";
import {
  findVectorStoreId,
  findVectorStoreIdForScenario,
  vectorStoreKeywordsForScenario,
} from "./presetScenarioIds";

describe("presetScenarioIds vector store mapping", () => {
  const stores = [
    { id: "vs-air", name: "air_risk_uk_nats_gps_closure-abc12345" },
    { id: "vs-port", name: "land_risk_port_strike_la-def67890" },
    { id: "vs-suez", name: "suez_blockage_analysis-ghi11223" },
  ];

  it("returns scenario-specific keywords", () => {
    expect(vectorStoreKeywordsForScenario("opensky-uk-closure-001")).toEqual([
      "uk",
      "nats",
      "gps",
      "air",
    ]);
    expect(vectorStoreKeywordsForScenario("supply-chain-port-strike-la")).toEqual([
      "port",
      "strike",
      "la",
    ]);
    expect(vectorStoreKeywordsForScenario("supply-chain-suez-blockage")).toEqual([
      "suez",
      "blockage",
    ]);
  });

  it("finds a store id by keywords", () => {
    expect(findVectorStoreId(stores, ["port", "strike"])).toBe("vs-port");
    expect(findVectorStoreId(stores, ["missing"])).toBe("");
  });

  it("resolves the vector store for each simulation scenario", () => {
    expect(findVectorStoreIdForScenario(stores, "opensky-uk-closure-001")).toBe("vs-air");
    expect(findVectorStoreIdForScenario(stores, "supply-chain-port-strike-la")).toBe("vs-port");
    expect(findVectorStoreIdForScenario(stores, "supply-chain-suez-blockage")).toBe("vs-suez");
  });
});
