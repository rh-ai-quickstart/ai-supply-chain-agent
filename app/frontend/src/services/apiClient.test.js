import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiGet, apiPost, apiPostFormData } from "./apiClient";

describe("apiClient", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  describe("apiGet", () => {
    it("throws when response is not ok", async () => {
      globalThis.fetch.mockResolvedValue({
        ok: false,
        status: 503,
        text: () => Promise.resolve(""),
      });
      await expect(apiGet("/api/v1/version")).rejects.toThrow("503");
    });

    it("prefers JSON error message from failure body", async () => {
      globalThis.fetch.mockResolvedValue({
        ok: false,
        status: 502,
        text: () => Promise.resolve(JSON.stringify({ error: "sim down" })),
      });
      await expect(apiGet("/api/v1/general-simulation/scenarios")).rejects.toThrow("sim down");
    });

    it("GETs JSON from default base URL + path", async () => {
      globalThis.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ ok: true }),
      });
      await expect(apiGet("/api/v1/version")).resolves.toEqual({ ok: true });
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/v1/version", { signal: undefined });
    });
  });

  describe("apiPost", () => {
    it("POSTs JSON body", async () => {
      globalThis.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ id: 1 }),
      });
      await expect(apiPost("/api/v1/chat", { input: "hi" })).resolves.toEqual({ id: 1 });
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/v1/chat",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input: "hi" }),
        })
      );
    });

    it("prefers JSON error message from failure body", async () => {
      globalThis.fetch.mockResolvedValue({
        ok: false,
        status: 400,
        text: () => Promise.resolve(JSON.stringify({ error: "bad question" })),
      });
      await expect(apiPost("/api/v1/general-simulation/query", {})).rejects.toThrow("bad question");
    });
  });

  describe("apiPostFormData", () => {
    it("returns JSON on success without setting Content-Type", async () => {
      const fd = new FormData();
      fd.append("name", "kb");
      globalThis.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ created: true }),
      });
      await expect(apiPostFormData("/api/v1/knowledge-bases", fd)).resolves.toEqual({ created: true });
      const [, init] = globalThis.fetch.mock.calls[0];
      expect(init.headers).toBeUndefined();
      expect(init.body).toBe(fd);
    });

    it("prefers JSON error message when error response body parses", async () => {
      globalThis.fetch.mockResolvedValue({
        ok: false,
        status: 400,
        text: () => Promise.resolve(JSON.stringify({ error: "bad file" })),
      });
      await expect(apiPostFormData("/api/v1/knowledge-bases", new FormData())).rejects.toThrow("bad file");
    });

    it("falls back to raw text on parse failure", async () => {
      globalThis.fetch.mockResolvedValue({
        ok: false,
        status: 422,
        text: () => Promise.resolve("plain failure"),
      });
      await expect(apiPostFormData("/x", new FormData())).rejects.toThrow("plain failure");
    });
  });
});
