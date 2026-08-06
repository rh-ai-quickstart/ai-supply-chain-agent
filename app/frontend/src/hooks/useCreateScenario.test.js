import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCreateScenario } from "./useCreateScenario";

const proposeScenario = vi.hoisted(() => vi.fn());
const createScenario = vi.hoisted(() => vi.fn());

vi.mock("../services/scenarioCreateService", () => ({
  proposeScenario: (...args) => proposeScenario(...args),
  createScenario: (...args) => createScenario(...args),
}));

describe("useCreateScenario", () => {
  beforeEach(() => {
    proposeScenario.mockReset();
    createScenario.mockReset();
  });

  it("does nothing when proposing an empty prompt", async () => {
    const { result } = renderHook(() => useCreateScenario());
    await act(async () => {
      await result.current.propose();
    });
    expect(proposeScenario).not.toHaveBeenCalled();
  });

  it("proposes a draft merged over the empty-draft defaults", async () => {
    proposeScenario.mockResolvedValue({
      success: true,
      draft: {
        name: "France Closure",
        scenario_id: "france-closure",
        description: "d",
        affect_bbox: "1,2,3,4",
      },
    });
    const { result } = renderHook(() => useCreateScenario());
    act(() => result.current.setPrompt("Close French airspace"));
    await act(async () => {
      await result.current.propose();
    });
    expect(result.current.draft).toMatchObject({
      name: "France Closure",
      scenario_id: "france-closure",
      place_summary: "",
      rationale: "",
    });
  });

  it("surfaces a propose error and clears the draft", async () => {
    proposeScenario.mockResolvedValue({ success: false, error: "nope" });
    const { result } = renderHook(() => useCreateScenario());
    act(() => result.current.setPrompt("x"));
    await act(async () => {
      await result.current.propose();
    });
    expect(result.current.error).toBe("nope");
    expect(result.current.draft).toBeNull();
  });

  it("updateDraftField is a no-op without an existing draft", () => {
    const { result } = renderHook(() => useCreateScenario());
    act(() => result.current.updateDraftField("name", "ignored"));
    expect(result.current.draft).toBeNull();
  });

  it("creates the scenario and calls onCreated with the new id", async () => {
    proposeScenario.mockResolvedValue({
      success: true,
      draft: { name: "n", scenario_id: "s", description: "d", affect_bbox: "1,2,3,4" },
    });
    createScenario.mockResolvedValue({ success: true, scenario_id: "s" });
    const onCreated = vi.fn();
    const { result } = renderHook(() => useCreateScenario(onCreated));
    act(() => result.current.setPrompt("x"));
    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.create();
    });
    expect(createScenario).toHaveBeenCalledWith(result.current.draft);
    expect(onCreated).toHaveBeenCalledWith("s");
  });

  it("surfaces a create error without calling onCreated", async () => {
    proposeScenario.mockResolvedValue({
      success: true,
      draft: { name: "n", scenario_id: "s", description: "d", affect_bbox: "1,2,3,4" },
    });
    createScenario.mockResolvedValue({ success: false, error: "boom" });
    const onCreated = vi.fn();
    const { result } = renderHook(() => useCreateScenario(onCreated));
    act(() => result.current.setPrompt("x"));
    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.create();
    });
    expect(result.current.error).toBe("boom");
    expect(onCreated).not.toHaveBeenCalled();
  });
});
