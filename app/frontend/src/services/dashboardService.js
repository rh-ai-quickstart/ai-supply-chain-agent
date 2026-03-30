import { apiGet, apiPost } from "./apiClient";

export function getDashboardState() {
  return apiGet("/api/v1/state");
}

export async function triggerWorldEvent(mapView) {
  return apiPost("/api/v1/trigger-event", { mapView });
}

export async function runSimulation({ scenario, optimize }) {
  return apiPost("/api/v1/simulate", { scenario, optimize });
}

export async function sendChatMessage(input, chatHistory = []) {
  return apiGet("/api/v1/chat", { input, chat_history: chatHistory });
}
