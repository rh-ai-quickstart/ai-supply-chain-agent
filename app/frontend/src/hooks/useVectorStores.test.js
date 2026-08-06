import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useVectorStores } from "./useVectorStores";

const getVectorStores = vi.hoisted(() => vi.fn());

vi.mock("../services/dashboardService", () => ({
  getVectorStores: (...args) => getVectorStores(...args),
}));

describe("useVectorStores", () => {
  beforeEach(() => {
    getVectorStores.mockReset();
  });

  it("loads vector stores on mount", async () => {
    getVectorStores.mockResolvedValue({ vector_stores: [{ id: "vs-1", name: "KB1" }] });
    const { result } = renderHook(() => useVectorStores());
    await waitFor(() => {
      expect(result.current.vectorStores).toEqual([{ id: "vs-1", name: "KB1" }]);
    });
    expect(result.current.vectorStoresError).toBe("");
  });

  it("sets an error message and clears the list when loading fails", async () => {
    getVectorStores.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useVectorStores());
    await waitFor(() => {
      expect(result.current.vectorStoresError).toBe(
        "Unable to load knowledge bases for chat retrieval.",
      );
    });
    expect(result.current.vectorStores).toEqual([]);
  });

  it("ignores AbortError from a cancelled reload", async () => {
    getVectorStores.mockRejectedValue(new DOMException("aborted", "AbortError"));
    const { result } = renderHook(() => useVectorStores());
    await act(async () => {
      await result.current.reloadVectorStores();
    });
    expect(result.current.vectorStoresError).toBe("");
  });

  it("exposes reloadVectorStores for callers (e.g. after a new KB is created)", async () => {
    getVectorStores.mockResolvedValueOnce({ vector_stores: [] });
    const { result } = renderHook(() => useVectorStores());
    await waitFor(() => expect(getVectorStores).toHaveBeenCalledTimes(1));

    getVectorStores.mockResolvedValueOnce({ vector_stores: [{ id: "vs-2", name: "KB2" }] });
    await act(async () => {
      await result.current.reloadVectorStores();
    });
    expect(result.current.vectorStores).toEqual([{ id: "vs-2", name: "KB2" }]);
  });
});
