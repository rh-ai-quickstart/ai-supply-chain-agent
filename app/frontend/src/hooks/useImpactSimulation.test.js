import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useImpactSimulation } from "./useImpactSimulation";

const listImpactScenarios = vi.hoisted(() => vi.fn());
const getImpactEntitiesGeoJson = vi.hoisted(() => vi.fn());
const runImpactQuery = vi.hoisted(() => vi.fn());

vi.mock("../services/generalSimulationService", () => ({
  listImpactScenarios: (...args) => listImpactScenarios(...args),
  getImpactEntitiesGeoJson: (...args) => getImpactEntitiesGeoJson(...args),
  runImpactQuery: (...args) => runImpactQuery(...args),
}));

describe("useImpactSimulation", () => {
  beforeEach(() => {
    listImpactScenarios.mockReset();
    getImpactEntitiesGeoJson.mockReset();
    runImpactQuery.mockReset();
    listImpactScenarios.mockResolvedValue({ success: true, scenarios: ["opensky-uk-closure-001"] });
    getImpactEntitiesGeoJson.mockResolvedValue({
      success: true,
      geojson: { type: "FeatureCollection", features: [] },
    });
  });

  it("loads scenarios on mount and preselects the initial scenario", async () => {
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));
    expect(result.current.scenarios).toEqual(["opensky-uk-closure-001"]);
    expect(result.current.scenarioId).toBe("opensky-uk-closure-001");
  });

  it("loads map entities with the global demo bbox and defaults to live map mode", async () => {
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));
    await waitFor(() =>
      expect(getImpactEntitiesGeoJson).toHaveBeenCalledWith(
        expect.objectContaining({
          bbox: "-130,20,50,62",
          limit: 3000,
        }),
      ),
    );
    expect(result.current.mapMode).toBe("live");
    expect(result.current.focusBbox).toBe("");
    expect(result.current.mapTitle).toBe("Live Flights");
  });

  it("switches focusBbox when map mode becomes scenario", async () => {
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    act(() => result.current.handleMapModeChange("scenario"));
    expect(result.current.mapMode).toBe("scenario");
    expect(result.current.focusBbox).toBe("-15,35,40,62");
    expect(result.current.mapTitle).toBe("Impact Map");
  });

  it("surfaces a scenarios-loading error", async () => {
    listImpactScenarios.mockResolvedValue({ success: false, error: "boom" });
    const { result } = renderHook(() => useImpactSimulation({}));
    await waitFor(() => expect(result.current.scenariosError).toBe("boom"));
  });

  it("derives highlightedIds/reroutes/valueByEntity/currency from a query result", async () => {
    runImpactQuery.mockResolvedValue({
      success: true,
      affected_entities: ["e1"],
      solver: {
        recommended_reroutes: [{ entity_id: "e1" }],
        value_breakdown: [{ entity_id: "e1", value_usd: 100 }],
        currency: "EUR",
      },
    });
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    await act(async () => {
      await result.current.handleRunQuery();
    });

    expect(result.current.highlightedIds).toEqual(["e1"]);
    expect(result.current.reroutes).toEqual([{ entity_id: "e1" }]);
    expect(result.current.currency).toBe("EUR");
    expect(result.current.valueByEntity.get("e1")).toBe(100);
  });

  it("surfaces a query error without touching the map", async () => {
    runImpactQuery.mockResolvedValue({ success: false, error: "query failed" });
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    await act(async () => {
      await result.current.handleRunQuery();
    });
    expect(result.current.queryError).toBe("query failed");
    expect(result.current.result).toBeNull();
  });

  it("handleFocusEntity sets focus state and clears any selected diversion", async () => {
    const { result } = renderHook(() => useImpactSimulation({}));
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    act(() => result.current.handleFocusDiversion({ entity_id: "e1", target_id: "e2" }));
    expect(result.current.selectedDiversionKey).toBe("e1|e2");

    act(() => result.current.handleFocusEntity("e3"));
    expect(result.current.focusedEntityId).toBe("e3");
    expect(result.current.focusNonce).toBe(2);
    expect(result.current.selectedDiversionKey).toBe("");
  });

  it("notifies onScenarioChange once a scenario id is selected", async () => {
    const onScenarioChange = vi.fn();
    renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001", onScenarioChange }),
    );
    await waitFor(() => expect(onScenarioChange).toHaveBeenCalledWith("opensky-uk-closure-001"));
  });

  it("runs the impact query automatically when the scenario is changed", async () => {
    listImpactScenarios.mockResolvedValue({
      success: true,
      scenarios: ["opensky-uk-closure-001", "supply-chain-port-strike-la"],
    });
    runImpactQuery.mockResolvedValue({ success: true, affected_entities: [] });
    const onScenarioChange = vi.fn();
    const { result } = renderHook(() => useImpactSimulation({ onScenarioChange }));
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    act(() => result.current.handleChangeScenarioId("supply-chain-port-strike-la"));

    expect(onScenarioChange).toHaveBeenCalledWith("supply-chain-port-strike-la");
    await waitFor(() =>
      expect(runImpactQuery).toHaveBeenCalledWith({
        scenarioId: "supply-chain-port-strike-la",
        question: expect.stringContaining("Port of Los Angeles"),
      }),
    );
    expect(result.current.mapMode).toBe("scenario");
  });

  it("runs the impact query from a suggested prompt and updates the question", async () => {
    runImpactQuery.mockResolvedValue({ success: true, affected_entities: [] });
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    await act(async () => {
      await result.current.handleRunSuggestedPrompt(
        "Show affected aircraft and recommend diversions.",
      );
    });

    expect(runImpactQuery).toHaveBeenCalledWith({
      scenarioId: "opensky-uk-closure-001",
      question: "Show affected aircraft and recommend diversions.",
    });
    expect(result.current.question).toBe("Show affected aircraft and recommend diversions.");
  });

  it("sets mapError when geojson load fails", async () => {
    getImpactEntitiesGeoJson.mockResolvedValue({
      success: false,
      error: "geojson unavailable",
    });
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.mapError).toBe("geojson unavailable"));
  });

  it("clears prior results when scenario changes", async () => {
    listImpactScenarios.mockResolvedValue({
      success: true,
      scenarios: ["opensky-uk-closure-001", "supply-chain-port-strike-la"],
    });
    runImpactQuery.mockResolvedValue({
      success: true,
      answer: "Impact summary",
      affected_entities: [],
      solver: { impact_score: 0.5 },
      tool_call_trace: [{ tool_name: "get_affected_subgraph" }],
    });
    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    await act(async () => {
      await result.current.handleRunQuery();
    });
    expect(result.current.result).not.toBeNull();

    act(() => result.current.handleChangeScenarioId("supply-chain-port-strike-la"));
    expect(result.current.result).toBeNull();
  });

  it("populates solver summary and tool trace from a successful query", async () => {
    runImpactQuery.mockResolvedValue({
      success: true,
      answer: "Twelve flights affected.",
      affected_entities: ["e1"],
      solver: { impact_score: 0.8, total_value_at_risk: 1000, currency: "USD" },
      tool_call_trace: [{ tool_name: "solve_impact", arguments: {}, output: {} }],
    });
    getImpactEntitiesGeoJson
      .mockResolvedValueOnce({
        success: true,
        geojson: { type: "FeatureCollection", features: [] },
      })
      .mockResolvedValueOnce({
        success: true,
        geojson: {
          type: "FeatureCollection",
          features: [{ type: "Feature", properties: { id: "e1" } }],
        },
      });

    const { result } = renderHook(() =>
      useImpactSimulation({ initialScenarioId: "opensky-uk-closure-001" }),
    );
    await waitFor(() => expect(result.current.scenariosLoading).toBe(false));

    await act(async () => {
      await result.current.handleRunQuery();
    });

    expect(result.current.result?.answer).toBe("Twelve flights affected.");
    expect(result.current.result?.solver?.impact_score).toBe(0.8);
    expect(result.current.result?.tool_call_trace).toHaveLength(1);
  });
});
