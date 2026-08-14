import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { useHashRoute } from "./useHashRoute";

function setHash(hash) {
  window.location.hash = hash;
}

function fireHashChange() {
  window.dispatchEvent(new Event("hashchange"));
}

describe("useHashRoute", () => {
  beforeEach(() => {
    setHash("#/simulation");
  });

  it("derives the initial view and scenario id from the hash", () => {
    setHash("#/simulation?scenario=opensky-uk-closure-001");
    const { result } = renderHook(() => useHashRoute());
    expect(result.current.activeView).toBe("simulation");
    expect(result.current.activeScenarioId).toBe("opensky-uk-closure-001");
  });

  it("recognizes the knowledge-bases view and treats create-scenario as simulation", () => {
    setHash("#/knowledge-bases");
    const { result: kb } = renderHook(() => useHashRoute());
    expect(kb.current.activeView).toBe("knowledge-bases");

    setHash("#/create-scenario");
    const { result: create } = renderHook(() => useHashRoute());
    expect(create.current.activeView).toBe("simulation");
  });

  it("redirects legacy #/live, #/create-scenario (and empty/dashboard) hash to #/simulation", () => {
    setHash("#/dashboard?scenario=abc");
    renderHook(() => useHashRoute());
    expect(window.location.hash).toBe("#/simulation?scenario=abc");

    setHash("#/live");
    renderHook(() => useHashRoute());
    expect(window.location.hash).toBe("#/simulation");

    setHash("#/create-scenario");
    renderHook(() => useHashRoute());
    expect(window.location.hash).toBe("#/simulation");
  });

  it("updates view/scenario id on hashchange events", () => {
    const { result } = renderHook(() => useHashRoute());
    act(() => {
      setHash("#/knowledge-bases");
      fireHashChange();
    });
    expect(result.current.activeView).toBe("knowledge-bases");
  });

  it("navigate() writes the expected hash for each view", () => {
    const { result } = renderHook(() => useHashRoute());

    act(() => result.current.navigate("knowledge-bases"));
    expect(window.location.hash).toBe("#/knowledge-bases");

    act(() => result.current.navigate("create-scenario"));
    expect(window.location.hash).toBe("#/simulation");

    act(() => result.current.navigate("live"));
    expect(window.location.hash).toBe("#/simulation");

    act(() => result.current.navigate("simulation", { scenarioId: "abc" }));
    expect(window.location.hash).toBe("#/simulation?scenario=abc");

    act(() => result.current.navigate("simulation"));
    expect(window.location.hash).toBe("#/simulation");
  });

  it("setActiveScenarioId updates state without touching the hash", () => {
    setHash("#/simulation?scenario=abc");
    const { result } = renderHook(() => useHashRoute());
    act(() => result.current.setActiveScenarioId("xyz"));
    expect(result.current.activeScenarioId).toBe("xyz");
    expect(window.location.hash).toBe("#/simulation?scenario=abc");
  });

  it("syncScenarioHash only rewrites the hash when the scenario differs", () => {
    setHash("#/simulation?scenario=abc");
    const { result } = renderHook(() => useHashRoute());

    act(() => result.current.syncScenarioHash("abc"));
    expect(window.location.hash).toBe("#/simulation?scenario=abc");

    act(() => result.current.syncScenarioHash("xyz"));
    expect(window.location.hash).toBe("#/simulation?scenario=xyz");
  });
});
