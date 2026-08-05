import { apiGet, apiPostStream } from "./apiClient";

function chatRequestBody(input, chatHistory, vectorStoreId, useVllm, scenarioId) {
  const trimmed = vectorStoreId && String(vectorStoreId).trim();
  const scenario = scenarioId && String(scenarioId).trim();
  return {
    input,
    use_vllm: useVllm,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
    ...(scenario ? { scenario_id: scenario } : {}),
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
  { signal, scenarioId } = {},
) {
  return apiPostStream(
    "/api/v1/chat",
    chatRequestBody(input, chatHistory, vectorStoreId, useVllm, scenarioId),
    onEvent,
    { signal },
  );
}
