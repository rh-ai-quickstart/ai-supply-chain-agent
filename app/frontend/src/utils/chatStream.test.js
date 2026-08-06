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

  it("attaches simulation payload from a tool done event", () => {
    const next = applyChatStreamEvent(base, {
      type: "done",
      answer: "Sim done",
      tool: "general_simulation",
      simulation: { scenario_id: "opensky-uk-closure-001", affected_entities: ["a"] },
    });
    expect(next?.[1].tool).toBe("general_simulation");
    expect(next?.[1].simulation).toEqual({
      scenario_id: "opensky-uk-closure-001",
      affected_entities: ["a"],
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
