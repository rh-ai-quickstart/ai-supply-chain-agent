import { describe, expect, it } from "vitest";
import {
  findVectorStoreNameForScenario,
  humanizeScenarioId,
  labelForScenario,
  suggestedPromptsForScenario,
} from "./presetScenarioIds";

describe("labelForScenario", () => {
  it("uses preset labels when known", () => {
    expect(labelForScenario("opensky-uk-closure-001")).toBe("UK Airspace Closure");
  });

  it("humanizes unknown scenario ids", () => {
    expect(labelForScenario("france-airspace-closure")).toBe("France Airspace Closure");
    expect(humanizeScenarioId("port_strike_marseille")).toBe("Port Strike Marseille");
  });
});

describe("suggestedPromptsForScenario", () => {
  it("returns suggested prompts for preset scenarios", () => {
    expect(suggestedPromptsForScenario("opensky-uk-closure-001").length).toBeGreaterThan(0);
  });

  it("returns an empty list for unknown scenarios", () => {
    expect(suggestedPromptsForScenario("custom-001")).toEqual([]);
  });
});

describe("findVectorStoreNameForScenario", () => {
  const stores = [
    { id: "vs-air", name: "air_risk_uk_nats_gps_closure-abc12345" },
    { id: "vs-port", name: "land_risk_port_strike_la-def67890" },
  ];

  it("returns the matching store name", () => {
    expect(findVectorStoreNameForScenario(stores, "opensky-uk-closure-001")).toBe(
      "air_risk_uk_nats_gps_closure-abc12345",
    );
  });

  it("returns empty when no store matches", () => {
    expect(findVectorStoreNameForScenario(stores, "unknown-scenario")).toBe("");
  });

  it("matches port and suez preset scenarios", () => {
    const extended = [
      ...stores,
      { id: "vs-suez", name: "suez_blockage_analysis-ghi11223" },
    ];
    expect(findVectorStoreNameForScenario(extended, "supply-chain-port-strike-la")).toBe(
      "land_risk_port_strike_la-def67890",
    );
    expect(findVectorStoreNameForScenario(extended, "supply-chain-suez-blockage")).toBe(
      "suez_blockage_analysis-ghi11223",
    );
  });

  it("matches a user-uploaded knowledge base to its scenario by descriptive name", () => {
    const userStores = [{ id: "vs-uk1", name: "UK Flight Data" }];
    expect(findVectorStoreNameForScenario(userStores, "opensky-uk-closure-001")).toBe(
      "UK Flight Data",
    );
  });

  it("never auto-selects the news vector store", () => {
    const withNews = [
      ...stores,
      { id: "vs-news", name: "supply-chain-news" },
    ];
    expect(findVectorStoreNameForScenario(withNews, "supply-chain-port-strike-la")).toBe(
      "land_risk_port_strike_la-def67890",
    );
  });
});
