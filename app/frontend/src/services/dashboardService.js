import { apiGet, apiPost } from "./apiClient";

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

export async function sendChatMessage(input, chatHistory = [], vectorStoreId) {
  const trimmed = vectorStoreId && String(vectorStoreId).trim();
  return apiPost("/api/v1/chat", {
    input,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
  });
}
