import { apiGet, apiPostStream } from "./apiClient";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);

function chatRequestBody(input, chatHistory, vectorStoreId, useVllm, scenarioId, impactResult) {
  const trimmed = vectorStoreId && String(vectorStoreId).trim();
  const scenario = scenarioId && String(scenarioId).trim();
  const impact =
    impactResult && typeof impactResult === "object" && !Array.isArray(impactResult)
      ? impactResult
      : null;
  return {
    input,
    use_vllm: useVllm,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
    ...(scenario ? { scenario_id: scenario } : {}),
    ...(impact ? { impact_result: impact } : {}),
  };
}

export function getVectorStores({ signal } = {}) {
  return apiGet("/api/v1/vector_stores", { signal });
}

export async function sendChatMessageStream(
  input,
  chatHistory = [],
  vectorStoreId,
  useVllm = true,
  onEvent,
  { signal, scenarioId, impactResult } = {},
) {
  return apiPostStream(
    "/api/v1/chat",
    chatRequestBody(input, chatHistory, vectorStoreId, useVllm, scenarioId, impactResult),
    onEvent,
    { signal },
  );
}
