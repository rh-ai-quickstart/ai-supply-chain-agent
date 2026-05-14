import { describe, expect, it, vi } from "vitest";
import { createKnowledgeBase, listKnowledgeBases } from "./knowledgeBasesService";

const mocks = vi.hoisted(() => ({
  getVectorStores: vi.fn(),
  apiGet: vi.fn(),
  apiPostFormData: vi.fn(),
}));

vi.mock("./dashboardService", () => ({
  getVectorStores: mocks.getVectorStores,
}));

vi.mock("./apiClient", () => ({
  apiGet: mocks.apiGet,
  apiPostFormData: mocks.apiPostFormData,
}));

describe("listKnowledgeBases", () => {
  it("merges catalog rows with vector stores and sorts by name", async () => {
    mocks.getVectorStores.mockResolvedValue({
      vector_stores: [
        { id: "vs-b", name: "Beta Store" },
        { id: "vs-a", name: "Alpha Store" },
      ],
    });
    mocks.apiGet.mockResolvedValue({
      knowledge_bases: [
        { name: "Alpha", vector_store_id: "vs-a", files: [], createdAt: "2020-01-01T00:00:00.000Z" },
      ],
    });

    const rows = await listKnowledgeBases();
    expect(rows.map((r) => r.name)).toEqual(["Alpha", "Beta Store"]);
    const beta = rows.find((r) => r.vector_store_id === "vs-b");
    expect(beta?.source).toBe("llamastack");
    expect(beta?.id).toBe("vs:vs-b");
  });

  it("includes catalog-only entries when vector store list does not contain them", async () => {
    mocks.getVectorStores.mockResolvedValue({ vector_stores: [] });
    mocks.apiGet.mockResolvedValue({
      knowledge_bases: [{ name: "Orphan", vector_store_id: "gone", files: [] }],
    });
    const rows = await listKnowledgeBases();
    expect(rows).toHaveLength(1);
    expect(rows[0].source).toBe("catalog_only");
  });
});

describe("createKnowledgeBase", () => {
  it("posts multipart form with name and files", async () => {
    mocks.apiPostFormData.mockResolvedValue({ ok: true });
    const file = new File(["x"], "doc.txt", { type: "text/plain" });
    await createKnowledgeBase("My KB", [file]);
    expect(mocks.apiPostFormData).toHaveBeenCalledTimes(1);
    const [, formData] = mocks.apiPostFormData.mock.calls[0];
    expect(formData.get("name")).toBe("My KB");
    expect(formData.getAll("files")).toEqual([file]);
  });
});
