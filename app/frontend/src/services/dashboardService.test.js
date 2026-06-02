import { beforeEach, describe, expect, it, vi } from "vitest";
import { sendChatMessage } from "./dashboardService";

const mocks = vi.hoisted(() => ({
  apiPostNdjsonStream: vi.fn(),
}));

vi.mock("./apiClient", () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPostNdjsonStream: mocks.apiPostNdjsonStream,
}));

describe("sendChatMessage", () => {
  beforeEach(() => {
    mocks.apiPostNdjsonStream.mockReset();
    mocks.apiPostNdjsonStream.mockResolvedValue(undefined);
  });

  it("streams from POST /api/v1/chat with input only", async () => {
    const onEvent = vi.fn();
    await sendChatMessage("hello", [], undefined, { onEvent });

    expect(mocks.apiPostNdjsonStream).toHaveBeenCalledWith(
      "/api/v1/chat",
      { input: "hello" },
      { onEvent, signal: undefined },
    );
  });

  it("includes chat_history and trimmed vector_store_id", async () => {
    await sendChatMessage(
      "q",
      [{ role: "human", content: "prev" }],
      "  vs-1  ",
      { onEvent: vi.fn() },
    );

    expect(mocks.apiPostNdjsonStream).toHaveBeenCalledWith(
      "/api/v1/chat",
      {
        input: "q",
        chat_history: [{ role: "human", content: "prev" }],
        vector_store_id: "vs-1",
      },
      expect.any(Object),
    );
  });
});
