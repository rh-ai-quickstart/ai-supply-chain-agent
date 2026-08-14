import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChatSession } from "./useChatSession";

const sendChatMessageStream = vi.hoisted(() => vi.fn());

vi.mock("../services/chatService", () => ({
  sendChatMessageStream: (...args) => sendChatMessageStream(...args),
}));

const VECTOR_STORES = [{ id: "vs-air", name: "air_risk_uk_nats_gps_closure-abc12345" }];

describe("useChatSession", () => {
  beforeEach(() => {
    sendChatMessageStream.mockReset();
  });

  it("computes a RAG hint when no vector store matches the active scenario", () => {
    const { result } = renderHook(() =>
      useChatSession({
        vectorStores: VECTOR_STORES,
        vectorStoresError: "",
        activeScenarioId: "supply-chain-suez-blockage",
      }),
    );
    expect(result.current.knowledgeBaseName).toBe("");
    expect(result.current.chatRagHint).toBe("");
  });

  it("exposes the matched knowledge-base name for the active scenario", () => {
    const { result } = renderHook(() =>
      useChatSession({
        vectorStores: VECTOR_STORES,
        vectorStoresError: "",
        activeScenarioId: "opensky-uk-closure-001",
      }),
    );
    expect(result.current.knowledgeBaseName).toBe("air_risk_uk_nats_gps_closure-abc12345");
  });

  it("updates the knowledge-base name when the active scenario changes", () => {
    const stores = [
      { id: "vs-air", name: "air_risk_uk_nats_gps_closure-abc12345" },
      { id: "vs-port", name: "land_risk_port_strike_la-def67890" },
    ];
    const { result, rerender } = renderHook(
      ({ activeScenarioId }) =>
        useChatSession({
          vectorStores: stores,
          vectorStoresError: "",
          activeScenarioId,
        }),
      { initialProps: { activeScenarioId: "opensky-uk-closure-001" } },
    );

    expect(result.current.knowledgeBaseName).toBe("air_risk_uk_nats_gps_closure-abc12345");

    rerender({ activeScenarioId: "supply-chain-port-strike-la" });
    expect(result.current.knowledgeBaseName).toBe("land_risk_port_strike_la-def67890");
  });

  it("surfaces the vector-store loading error as the RAG hint", () => {
    const { result } = renderHook(() =>
      useChatSession({ vectorStores: [], vectorStoresError: "boom", activeScenarioId: "x" }),
    );
    expect(result.current.chatRagHint).toBe("boom");
  });

  it("keeps a separate chat input thread per scenario", () => {
    const { result, rerender } = renderHook(
      ({ activeScenarioId }) =>
        useChatSession({ vectorStores: [], vectorStoresError: "", activeScenarioId }),
      { initialProps: { activeScenarioId: "scenario-a" } },
    );

    act(() => result.current.handleChangeChatInput("hello a"));
    expect(result.current.chatInput).toBe("hello a");

    rerender({ activeScenarioId: "scenario-b" });
    expect(result.current.chatInput).toBe("");

    rerender({ activeScenarioId: "scenario-a" });
    expect(result.current.chatInput).toBe("hello a");
  });

  it("streams deltas into a placeholder message and resolves with the final answer", async () => {
    sendChatMessageStream.mockImplementation(async (_input, _history, _vs, _vllm, onEvent) => {
      onEvent({ type: "delta", content: "Hello " });
      onEvent({ type: "delta", content: "world" });
      onEvent({ type: "done", answer: "Hello world", completion: { model: "test" } });
    });

    const { result } = renderHook(() =>
      useChatSession({
        vectorStores: VECTOR_STORES,
        vectorStoresError: "",
        activeScenarioId: "opensky-uk-closure-001",
      }),
    );

    act(() => result.current.handleChangeChatInput("hi"));
    await act(async () => {
      await result.current.handleSubmitChat();
    });

    expect(result.current.chatMessages.at(-1)).toMatchObject({
      role: "ai",
      content: "Hello world",
    });
    expect(result.current.chatInput).toBe("");
    expect(result.current.chatLoading).toBe(false);
    expect(sendChatMessageStream).toHaveBeenCalledWith(
      "hi",
      expect.any(Array),
      "vs-air",
      true,
      expect.any(Function),
      expect.objectContaining({ scenarioId: "opensky-uk-closure-001" }),
    );
  });

  it("captures a simulation payload from a done event", async () => {
    sendChatMessageStream.mockImplementation(async (_input, _history, _vs, _vllm, onEvent) => {
      onEvent({ type: "done", answer: "ok", simulation: { affected_entities: ["a"] } });
    });
    const { result } = renderHook(() =>
      useChatSession({ vectorStores: [], vectorStoresError: "", activeScenarioId: "" }),
    );
    act(() => result.current.handleChangeChatInput("hi"));
    await act(async () => {
      await result.current.handleSubmitChat();
    });
    expect(result.current.chatSimulation).toMatchObject({
      affected_entities: ["a"],
      answer: "ok",
      success: true,
    });
  });

  it("sendPrompt adds the prompt to the chat as a human message and streams a reply", async () => {
    sendChatMessageStream.mockImplementation(async (_input, history, _vs, _vllm, onEvent) => {
      onEvent({ type: "delta", content: "Aircraft BAW442 " });
      onEvent({
        type: "done",
        answer: "Aircraft BAW442 should divert to EIDW",
        completion: { model: "test" },
      });
      expect(history.at(-1)).toMatchObject({ role: "human", content: "Show affected aircraft." });
    });

    const { result } = renderHook(() =>
      useChatSession({ vectorStores: [], vectorStoresError: "", activeScenarioId: "scenario-x" }),
    );

    await act(async () => {
      await result.current.sendPrompt("Show affected aircraft.");
    });

    expect(result.current.chatMessages[0]).toMatchObject({
      role: "human",
      content: "Show affected aircraft.",
    });
    expect(result.current.chatMessages.at(-1)).toMatchObject({
      role: "ai",
      content: "Aircraft BAW442 should divert to EIDW",
    });
    expect(result.current.chatLoading).toBe(false);
    expect(sendChatMessageStream).toHaveBeenCalledWith(
      "Show affected aircraft.",
      expect.any(Array),
      undefined,
      true,
      expect.any(Function),
      expect.objectContaining({ scenarioId: "scenario-x" }),
    );
  });

  it("sendPrompt does nothing when the prompt is empty", async () => {
    const { result } = renderHook(() =>
      useChatSession({ vectorStores: [], vectorStoresError: "", activeScenarioId: "x" }),
    );
    await act(async () => {
      await result.current.sendPrompt("   ");
    });
    expect(sendChatMessageStream).not.toHaveBeenCalled();
  });

  it("records an error message and restores history when the request fails", async () => {
    sendChatMessageStream.mockRejectedValue(new Error("network down"));
    const { result } = renderHook(() =>
      useChatSession({ vectorStores: [], vectorStoresError: "", activeScenarioId: "" }),
    );
    act(() => result.current.handleChangeChatInput("hi"));
    await act(async () => {
      await result.current.handleSubmitChat();
    });
    expect(result.current.chatError).toBe("network down");
    expect(result.current.chatMessages.at(-1)).toMatchObject({ role: "human", content: "hi" });
  });

  it("does nothing when submitting an empty question", async () => {
    const { result } = renderHook(() =>
      useChatSession({ vectorStores: [], vectorStoresError: "", activeScenarioId: "" }),
    );
    await act(async () => {
      await result.current.handleSubmitChat();
    });
    expect(sendChatMessageStream).not.toHaveBeenCalled();
  });
});
