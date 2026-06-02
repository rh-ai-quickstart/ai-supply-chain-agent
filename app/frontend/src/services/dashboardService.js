import { apiGet, apiPost, apiPostNdjsonStream } from "./apiClient";

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

function chatRequestBody(input, chatHistory, vectorStoreId) {
  const trimmed = vectorStoreId && String(vectorStoreId).trim();
  return {
    input,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
  };
}

export async function sendChatMessage(
  input,
  chatHistory = [],
  vectorStoreId,
  { onEvent, signal } = {},
) {
  return apiPostNdjsonStream(
    "/api/v1/chat",
    chatRequestBody(input, chatHistory, vectorStoreId),
    { onEvent, signal },
  );
}
