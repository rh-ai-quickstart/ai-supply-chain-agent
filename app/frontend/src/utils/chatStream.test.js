import { describe, expect, it } from "vitest";
import { applyChatStreamEvent, consumeChatSseStream } from "./chatStream.js";

describe("applyChatStreamEvent", () => {
  const base = [
    { role: "human", content: "hi" },
    { role: "ai", content: "", completion: null },
  ];

  it("appends delta text to the trailing AI message", () => {
    const next = applyChatStreamEvent(base, { type: "delta", content: "Hello" });
    expect(next?.[1].content).toBe("Hello");
  });

  it("finalizes answer and completion on done", () => {
    const next = applyChatStreamEvent(
      [{ role: "human", content: "hi" }, { role: "ai", content: "partial", completion: null }],
      { type: "done", answer: "final", completion: { usage: { total_tokens: 3 } } },
    );
    expect(next?.[1]).toEqual({
      role: "ai",
      content: "final",
      completion: { usage: { total_tokens: 3 } },
    });
  });
});

describe("consumeChatSseStream", () => {
  it("parses SSE data events from a readable stream", async () => {
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            'data: {"type":"delta","content":"Hi"}\n\ndata: {"type":"done","answer":"Hi","completion":null}\n\n',
          ),
        );
        controller.close();
      },
    });
    const response = new Response(body);
    const events = [];
    await consumeChatSseStream(response, (event) => events.push(event));
    expect(events).toEqual([
      { type: "delta", content: "Hi" },
      { type: "done", answer: "Hi", completion: null },
    ]);
  });
});
