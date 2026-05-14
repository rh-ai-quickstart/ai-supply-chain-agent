import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useDashboardState } from "./useDashboardState";

const getDashboardState = vi.hoisted(() => vi.fn());

vi.mock("../services/dashboardService", () => ({
  getDashboardState,
}));

describe("useDashboardState", () => {
  beforeEach(() => {
    getDashboardState.mockReset();
    getDashboardState.mockResolvedValue({ kpis: {}, alerts: {}, mapData: {}, charts: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads dashboard state on mount", async () => {
    const { result } = renderHook(() => useDashboardState());
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(getDashboardState).toHaveBeenCalled();
    expect(result.current.error).toBe("");
    expect(result.current.dashboardState).toEqual({ kpis: {}, alerts: {}, mapData: {}, charts: {} });
  });

  it("sets error when getDashboardState rejects", async () => {
    getDashboardState.mockRejectedValueOnce(new Error("network"));
    const { result } = renderHook(() => useDashboardState());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toMatch(/Unable to load dashboard/);
    expect(result.current.dashboardState).toBeNull();
  });
});
