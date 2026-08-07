import { beforeEach, describe, expect, it, vi } from "vitest";

const apiGet = vi.hoisted(() => vi.fn());
const apiPostStream = vi.hoisted(() => vi.fn());

vi.mock("./apiClient", () => ({
  apiGet: (...args) => apiGet(...args),
  apiPostStream: (...args) => apiPostStream(...args),
}));

import { getVectorStores, sendChatMessageStream } from "./chatService";

describe("chatService", () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPostStream.mockReset();
  });

  it("getVectorStores GETs /api/v1/vector_stores", async () => {
    const signal = AbortSignal.timeout(1000);
    apiGet.mockResolvedValue({ vector_stores: [] });
    await expect(getVectorStores({ signal })).resolves.toEqual({ vector_stores: [] });
    expect(apiGet).toHaveBeenCalledWith("/api/v1/vector_stores", { signal });
  });

  it("sendChatMessageStream posts minimal body without history or ids", async () => {
    const onEvent = vi.fn();
    apiPostStream.mockResolvedValue(undefined);
    await sendChatMessageStream("hello", [], "", true, onEvent);
    expect(apiPostStream).toHaveBeenCalledWith(
      "/api/v1/chat",
      { input: "hello", use_vllm: true },
      onEvent,
      { signal: undefined },
    );
  });

  it("sendChatMessageStream includes history, vector store, and scenario", async () => {
    const onEvent = vi.fn();
    const signal = AbortSignal.timeout(1000);
    const history = [{ role: "human", content: "prior" }];
    apiPostStream.mockResolvedValue(undefined);
    await sendChatMessageStream("follow up", history, " vs_1 ", false, onEvent, {
      signal,
      scenarioId: " opensky-uk-closure-001 ",
    });
    expect(apiPostStream).toHaveBeenCalledWith(
      "/api/v1/chat",
      {
        input: "follow up",
        use_vllm: false,
        chat_history: history,
        vector_store_id: "vs_1",
        scenario_id: "opensky-uk-closure-001",
      },
      onEvent,
      { signal },
    );
  });

  it("omits blank vector_store_id and scenario_id", async () => {
    apiPostStream.mockResolvedValue(undefined);
    await sendChatMessageStream("hi", [], "   ", true, vi.fn(), { scenarioId: "  " });
    expect(apiPostStream.mock.calls[0][1]).toEqual({
      input: "hi",
      use_vllm: true,
    });
  });
});
