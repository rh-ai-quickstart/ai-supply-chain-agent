import { describe, expect, it, vi } from "vitest";
import { handleChatStreamEvent } from "./handleChatStreamEvent";

function createHarness() {
  let message = { role: "ai", content: "", streaming: true, completion: null };
  const updateStreamingMessage = vi.fn((updater) => {
    message = updater(message);
  });
  const setChatError = vi.fn();
  const options = {
    updateStreamingMessage,
    setChatError,
    emptyAnswerText: "empty",
    streamFailedText: "stream failed",
  };
  return { message: () => message, setChatError, updateStreamingMessage, options };
}

describe("handleChatStreamEvent", () => {
  it("ignores invalid events", () => {
    const { updateStreamingMessage, options } = createHarness();
    handleChatStreamEvent(null, options);
    handleChatStreamEvent({ event: 1 }, options);
    expect(updateStreamingMessage).not.toHaveBeenCalled();
  });

  it("appends token deltas", () => {
    const { message, options } = createHarness();
    handleChatStreamEvent({ event: "token", delta: "Hel" }, options);
    handleChatStreamEvent({ event: "token", delta: "lo" }, options);
    expect(message().content).toBe("Hello");
    expect(message().streaming).toBe(true);
  });

  it("finalizes on message with routeData", () => {
    const { message, options } = createHarness();
    const routeData = { type: "route" };
    handleChatStreamEvent(
      { event: "message", answer: "Route ready", completion: { id: "1" }, routeData },
      options,
    );
    expect(message()).toMatchObject({
      content: "Route ready",
      streaming: false,
      completion: { id: "1" },
      routeData,
    });
  });

  it("finalizes on done and uses fallback for empty answer", () => {
    const { message, options } = createHarness();
    handleChatStreamEvent({ event: "done", answer: "  ", completion: null }, options);
    expect(message().content).toBe("empty");
    expect(message().streaming).toBe(false);
  });

  it("sets error state on error event", () => {
    const { message, setChatError, options } = createHarness();
    handleChatStreamEvent({ event: "error", message: "upstream down" }, options);
    expect(setChatError).toHaveBeenCalledWith("upstream down");
    expect(message().streaming).toBe(false);
  });
});
