import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useKnowledgeBases } from "./useKnowledgeBases";

const listKnowledgeBases = vi.hoisted(() => vi.fn());
const createKnowledgeBase = vi.hoisted(() => vi.fn());

vi.mock("../services/knowledgeBasesService", () => ({
  listKnowledgeBases: (...args) => listKnowledgeBases(...args),
  createKnowledgeBase: (...args) => createKnowledgeBase(...args),
}));

describe("useKnowledgeBases", () => {
  beforeEach(() => {
    listKnowledgeBases.mockReset();
    createKnowledgeBase.mockReset();
  });

  it("loads the catalog on mount", async () => {
    listKnowledgeBases.mockResolvedValue([{ id: "kb-1", name: "KB1" }]);
    const { result } = renderHook(() => useKnowledgeBases());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.rows).toEqual([{ id: "kb-1", name: "KB1" }]);
  });

  it("sets a load error when the catalog fetch fails", async () => {
    listKnowledgeBases.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useKnowledgeBases());
    await waitFor(() => expect(result.current.loadError).toBe("Unable to load knowledge bases."));
  });

  it("rejects submit without a name or files", async () => {
    listKnowledgeBases.mockResolvedValue([]);
    const { result } = renderHook(() => useKnowledgeBases());
    await waitFor(() => expect(result.current.loading).toBe(false));

    let created;
    await act(async () => {
      created = await result.current.submit("", [{}]);
    });
    expect(created).toBe(false);
    expect(createKnowledgeBase).not.toHaveBeenCalled();
  });

  it("creates a knowledge base, clears the name, and notifies + refreshes", async () => {
    listKnowledgeBases.mockResolvedValueOnce([]).mockResolvedValueOnce([{ id: "kb-1", name: "KB1" }]);
    createKnowledgeBase.mockResolvedValue({ warnings: [] });
    const onCreated = vi.fn();
    const { result } = renderHook(() => useKnowledgeBases(onCreated));
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => result.current.setName("KB1"));
    let created;
    await act(async () => {
      created = await result.current.submit("KB1", [{ name: "a.txt" }]);
    });

    expect(created).toBe(true);
    expect(createKnowledgeBase).toHaveBeenCalledWith("KB1", [{ name: "a.txt" }]);
    expect(result.current.name).toBe("");
    expect(onCreated).toHaveBeenCalledTimes(1);
    expect(result.current.rows).toEqual([{ id: "kb-1", name: "KB1" }]);
  });

  it("surfaces a submit error and resets saving", async () => {
    listKnowledgeBases.mockResolvedValue([]);
    createKnowledgeBase.mockRejectedValue(new Error("upload failed"));
    const { result } = renderHook(() => useKnowledgeBases());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.submit("KB1", [{ name: "a.txt" }]);
    });
    expect(result.current.submitError).toBe("upload failed");
    expect(result.current.saving).toBe(false);
  });

  it("surfaces warnings returned from a partially-successful upload", async () => {
    listKnowledgeBases.mockResolvedValue([]);
    createKnowledgeBase.mockResolvedValue({ warnings: ["file x skipped"] });
    const { result } = renderHook(() => useKnowledgeBases());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.submit("KB1", [{ name: "a.txt" }]);
    });
    expect(result.current.warnings).toEqual(["file x skipped"]);
  });
});
