import { afterEach, describe, expect, it, vi } from "vitest";
import { apiPostNdjsonStream, parseNdjsonBuffer } from "./apiClient";

function ndjsonFetchResponse(lines) {
  const encoder = new TextEncoder();
  const chunks = lines.map((line) => encoder.encode(`${line}\n`));
  let index = 0;
  const body = new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(chunks[index]);
        index += 1;
      } else {
        controller.close();
      }
    },
  });
  return { ok: true, body };
}

describe("apiPostNdjsonStream", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("invokes onEvent for each NDJSON line from the response body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        ndjsonFetchResponse([
          '{"event":"start"}',
          '{"event":"token","delta":"Hi"}',
          '{"event":"done","answer":"Hi"}',
        ]),
      ),
    );

    const events = [];
    await apiPostNdjsonStream("/api/v1/chat", { input: "q" }, {
      onEvent: (evt) => events.push(evt),
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/chat",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Accept: "application/x-ndjson",
        }),
      }),
    );
    expect(events).toEqual([
      { event: "start" },
      { event: "token", delta: "Hi" },
      { event: "done", answer: "Hi" },
    ]);
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 502 }));

    await expect(
      apiPostNdjsonStream("/api/v1/chat", { input: "q" }, { onEvent: () => {} }),
    ).rejects.toThrow("Request failed: 502");
  });

  it("returns quietly when fetch aborts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("Aborted", "AbortError")),
    );

    await expect(
      apiPostNdjsonStream("/api/v1/chat", { input: "q" }, { onEvent: () => {} }),
    ).resolves.toBeUndefined();
  });
});

describe("parseNdjsonBuffer", () => {
  it("parses complete lines and keeps a partial remainder", () => {
    const { events, remainder } = parseNdjsonBuffer(
      '{"event":"start"}\n{"event":"token","delta":"Hi"}\n{"event":"tok',
    );
    expect(events).toEqual([
      { event: "start" },
      { event: "token", delta: "Hi" },
    ]);
    expect(remainder).toBe('{"event":"tok');
  });

  it("ignores blank lines", () => {
    const { events, remainder } = parseNdjsonBuffer('\n\n{"event":"done"}\n\n');
    expect(events).toEqual([{ event: "done" }]);
    expect(remainder).toBe("");
  });
});
