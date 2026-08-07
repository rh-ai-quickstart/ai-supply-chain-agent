import { beforeEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());

vi.mock("./apiClient", () => ({
  apiGet: (...args) => apiGet(...args),
}));

import { getNews } from "./newsService";

describe("newsService", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiGet.mockResolvedValue({ items: [] });
  });

  it("defaults limit to 30", async () => {
    await getNews();
    expect(apiGet).toHaveBeenCalledWith("/api/v1/news?limit=30", { signal: undefined });
  });

  it("clamps limit to [1, 50]", async () => {
    const signal = AbortSignal.timeout(1000);
    await getNews({ signal, limit: 0 });
    expect(apiGet).toHaveBeenCalledWith("/api/v1/news?limit=1", { signal });
    await getNews({ limit: 99 });
    expect(apiGet).toHaveBeenCalledWith("/api/v1/news?limit=50", { signal: undefined });
  });

  it("falls back to 30 for non-numeric limit", async () => {
    await getNews({ limit: "nope" });
    expect(apiGet).toHaveBeenCalledWith("/api/v1/news?limit=30", { signal: undefined });
  });
});
