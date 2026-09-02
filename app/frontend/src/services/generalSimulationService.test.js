import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getImpactEntitiesGeoJson,
  listImpactScenarios,
  runImpactQuery,
} from "./generalSimulationService";

vi.mock("./apiClient", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiGet, apiPost } from "./apiClient";

describe("generalSimulationService", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockReset();
    vi.mocked(apiPost).mockReset();
  });

  it("lists scenarios", async () => {
    vi.mocked(apiGet).mockResolvedValue({ success: true, scenarios: ["a"] });
    await expect(listImpactScenarios()).resolves.toEqual({ success: true, scenarios: ["a"] });
    expect(apiGet).toHaveBeenCalledWith("/api/v1/general-simulation/scenarios", {
      signal: undefined,
    });
  });

  it("builds geojson query params", async () => {
    vi.mocked(apiGet).mockResolvedValue({ success: true });
    await getImpactEntitiesGeoJson({
      bbox: "-15,35,40,62",
      ids: ["opensky-1", "opensky-2"],
      limit: 10,
    });
    expect(apiGet).toHaveBeenCalledWith(
      "/api/v1/general-simulation/entities/geojson?bbox=-15%2C35%2C40%2C62&ids=opensky-1%2Copensky-2&limit=10",
      { signal: undefined },
    );
  });

  it("posts an impact query", async () => {
    vi.mocked(apiPost).mockResolvedValue({ success: true });
    await runImpactQuery({ question: "What is affected?", scenarioId: "opensky-uk-closure-001" });
    expect(apiPost).toHaveBeenCalledWith("/api/v1/general-simulation/query", {
      question: "What is affected?",
      scenario_id: "opensky-uk-closure-001",
    });
  });

  it("propagates apiPost errors from runImpactQuery", async () => {
    vi.mocked(apiPost).mockRejectedValue(new Error("network down"));
    await expect(
      runImpactQuery({ question: "q", scenarioId: "s1" }),
    ).rejects.toThrow("network down");
  });

  it("builds geojson url without params when none provided", async () => {
    vi.mocked(apiGet).mockResolvedValue({ success: true });
    await getImpactEntitiesGeoJson();
    expect(apiGet).toHaveBeenCalledWith(
      "/api/v1/general-simulation/entities/geojson",
      { signal: undefined },
    );
  });

  it("propagates apiGet errors from listImpactScenarios", async () => {
    vi.mocked(apiGet).mockRejectedValue(new Error("service unavailable"));
    await expect(listImpactScenarios()).rejects.toThrow("service unavailable");
  });
});
