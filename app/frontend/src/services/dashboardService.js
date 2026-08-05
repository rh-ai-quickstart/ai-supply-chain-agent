import { apiGet, apiPostStream } from "./apiClient";

function chatRequestBody(input, chatHistory, vectorStoreId, useVllm) {
  const trimmed = vectorStoreId && String(vectorStoreId).trim();
  return {
    input,
    use_vllm: useVllm,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
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
  { signal } = {},
) {
  return apiPostStream(
    "/api/v1/chat",
    chatRequestBody(input, chatHistory, vectorStoreId, useVllm),
    onEvent,
    { signal },
  );
}
