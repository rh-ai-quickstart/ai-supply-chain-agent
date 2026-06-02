/**
 * HTTP client for `app/backend/api` (Flask) routes. Paths must stay in sync with `app/backend/api/main.py`.
 */
import type { ChatMessage, ChatStreamEvent, DashboardState, VectorStoreSummary } from '../../types/dashboard';
import { apiGet, apiPost, apiPostNdjsonStream } from '../../services/apiClient';

export function fetchDashboardState(): Promise<DashboardState> {
  return apiGet<DashboardState>('/api/v1/state');
}

export function postTriggerWorldEvent(mapView: string): Promise<DashboardState> {
  return apiPost<DashboardState>('/api/v1/trigger-event', { mapView });
}

export function postSimulation(scenario: string, optimize: boolean): Promise<DashboardState> {
  return apiPost<DashboardState>('/api/v1/simulate', { scenario, optimize });
}

export function fetchVectorStores(): Promise<{
  vector_stores: VectorStoreSummary[];
  error?: string;
}> {
  return apiGet<{ vector_stores: VectorStoreSummary[]; error?: string }>('/api/v1/vector_stores');
}

function chatRequestBody(input: string, chatHistory: ChatMessage[], vectorStoreId?: string) {
  const trimmed = vectorStoreId?.trim();
  return {
    input,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
  };
}

/** NDJSON stream from ``POST /api/v1/chat`` (`start`, `token`, `done`, or `message`). */
export function postAssistantMessage(
  input: string,
  chatHistory: ChatMessage[] = [],
  vectorStoreId?: string,
  options: { onEvent: (_evt: ChatStreamEvent) => void; signal?: AbortSignal } = {
    onEvent: () => undefined,
  },
): Promise<void> {
  return apiPostNdjsonStream(
    '/api/v1/chat',
    chatRequestBody(input, chatHistory, vectorStoreId),
    options,
  );
}
