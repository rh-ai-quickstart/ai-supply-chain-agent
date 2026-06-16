import { apiGet, apiPost, apiPostStream } from "./apiClient";

function chatRequestBody(input, chatHistory, vectorStoreId, useVllm) {
  const trimmed = vectorStoreId && String(vectorStoreId).trim();
  return {
    input,
    use_vllm: useVllm,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
  };
}

export function getDashboardState() {
  return apiGet("/api/v1/state");
}

export function getVectorStores() {
  return apiGet("/api/v1/vector_stores");
}

export async function triggerWorldEvent(mapView) {
  return apiPost("/api/v1/trigger-event", { mapView });
}

export async function runSimulation({ scenario, optimize }) {
  return apiPost("/api/v1/simulate", { scenario, optimize });
}

export async function sendChatMessage(input, chatHistory = [], vectorStoreId, useVllm = true) {
  return apiPost("/api/v1/chat", chatRequestBody(input, chatHistory, vectorStoreId, useVllm));
}

export async function sendChatMessageStream(
  input,
  chatHistory = [],
  vectorStoreId,
  useVllm = true,
  onEvent,
) {
  return apiPostStream("/api/v1/chat", chatRequestBody(input, chatHistory, vectorStoreId, useVllm), onEvent);
}
