import { useCallback, useEffect, useRef, useState } from "react";
import { sendChatMessageStream } from "../services/chatService";
import {
  findVectorStoreIdForScenario,
  findVectorStoreNameForScenario,
} from "../services/presetScenarioIds";
import { applyChatStreamEvent } from "../utils/chatStream.js";

function chatKeyForScenario(scenarioId) {
  return scenarioId || "_default";
}

/**
 * Chat streaming orchestration, extracted from `App.jsx` (SRP): keeps a
 * separate message/input/error/loading thread per scenario, matches the
 * active scenario to a vector store for RAG, and streams `/api/v1/chat`
 * via `sendChatMessageStream`. `abortActiveStream` is exposed so callers
 * (e.g. a scenario switch) can cancel an in-flight request from outside.
 */
export function useChatSession({ vectorStores, vectorStoresError, activeScenarioId }) {
  const [chatMessagesByScenario, setChatMessagesByScenario] = useState({});
  const [chatInputByScenario, setChatInputByScenario] = useState({});
  const [chatErrorByScenario, setChatErrorByScenario] = useState({});
  const [chatLoadingByScenario, setChatLoadingByScenario] = useState({});
  const [chatSimulation, setChatSimulation] = useState(null);
  const chatAbortRef = useRef(null);

  const chatKey = chatKeyForScenario(activeScenarioId);
  const chatMessages = chatMessagesByScenario[chatKey] || [];
  const chatInput = chatInputByScenario[chatKey] || "";
  const chatError = chatErrorByScenario[chatKey] || "";
  const chatLoading = Boolean(chatLoadingByScenario[chatKey]);
  const matchedVectorStoreId = findVectorStoreIdForScenario(vectorStores, activeScenarioId);
  const knowledgeBaseName = findVectorStoreNameForScenario(vectorStores, activeScenarioId);
  const chatRagHint = vectorStoresError || "";

  useEffect(() => {
    return () => {
      chatAbortRef.current?.abort();
    };
  }, []);

  const abortActiveStream = useCallback(() => {
    chatAbortRef.current?.abort();
    chatAbortRef.current = null;
  }, []);

  const handleChangeChatInput = useCallback(
    (value) => {
      setChatInputByScenario((prev) => ({ ...prev, [chatKey]: value }));
    },
    [chatKey],
  );

  const submitChat = useCallback(
    async (text) => {
      const question = text.trim();
      if (!question || chatLoading) {
        return;
      }

      const scenarioKey = chatKey;
      const vectorStoreId = matchedVectorStoreId;
      const humanMessage = { role: "human", content: question };
      const historyForApi = [...(chatMessagesByScenario[scenarioKey] || []), humanMessage];
      const aiPlaceholder = { role: "ai", content: "", completion: null };

      chatAbortRef.current?.abort();
      const controller = new AbortController();
      chatAbortRef.current = controller;

      setChatMessagesByScenario((prev) => ({
        ...prev,
        [scenarioKey]: [...historyForApi, aiPlaceholder],
      }));
      setChatInputByScenario((prev) => ({ ...prev, [scenarioKey]: "" }));
      setChatErrorByScenario((prev) => ({ ...prev, [scenarioKey]: "" }));
      setChatLoadingByScenario((prev) => ({ ...prev, [scenarioKey]: true }));
      try {
        await sendChatMessageStream(
          question,
          historyForApi,
          vectorStoreId.trim() || undefined,
          true,
          (event) => {
            if (controller.signal.aborted) return;
            if (event?.type === "done" && event.simulation) {
              setChatSimulation({
                ...event.simulation,
                answer: event.answer || event.simulation.answer,
                success: true,
              });
            }
            setChatMessagesByScenario((prev) => {
              const current = prev[scenarioKey] || [];
              const next = applyChatStreamEvent(current, event);
              return next ? { ...prev, [scenarioKey]: next } : prev;
            });
          },
          { signal: controller.signal, scenarioId: activeScenarioId },
        );
      } catch (err) {
        if (err?.name === "AbortError") return;
        setChatErrorByScenario((prev) => ({
          ...prev,
          [scenarioKey]:
            err instanceof Error && err.message ? err.message : "Failed to send chat request.",
        }));
        setChatMessagesByScenario((prev) => ({ ...prev, [scenarioKey]: historyForApi }));
      } finally {
        if (chatAbortRef.current === controller) {
          chatAbortRef.current = null;
        }
        setChatLoadingByScenario((prev) => ({ ...prev, [scenarioKey]: false }));
      }
    },
    [chatLoading, chatKey, matchedVectorStoreId, chatMessagesByScenario, activeScenarioId],
  );

  const handleSubmitChat = useCallback(() => {
    return submitChat(chatInput);
  }, [submitChat, chatInput]);

  /**
   * Send an arbitrary prompt (e.g. a suggested-prompt chip) through the chat
   * agent. Unlike `handleSubmitChat` it does not read the input box, so callers
   * can trigger a prompt without typing it.
   */
  const sendPrompt = useCallback(
    (text) => {
      return submitChat(text);
    },
    [submitChat],
  );

  return {
    chatMessages,
    chatInput,
    chatError,
    chatLoading,
    chatRagHint,
    knowledgeBaseName,
    chatSimulation,
    handleChangeChatInput,
    handleSubmitChat,
    sendPrompt,
    abortActiveStream,
  };
}
