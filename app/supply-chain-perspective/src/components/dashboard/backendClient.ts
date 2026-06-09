/**
 * HTTP client for `app/backend/api` (Flask) routes. Paths must stay in sync with `app/backend/api/main.py`.
 */
import type { ChatApiResponse, ChatMessage, DashboardState, VectorStoreSummary } from '../../types/dashboard';
import { apiGet, apiPost } from '../../services/apiClient';

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

/** Matches legacy dashboard: `{ input, chat_history, vector_store_id?, use_vllm }`. */
export function postAssistantMessage(
  input: string,
  chatHistory: ChatMessage[] = [],
  vectorStoreId?: string,
  useVllm = true,
): Promise<ChatApiResponse> {
  const trimmed = vectorStoreId?.trim();
  return apiPost<ChatApiResponse>('/api/v1/chat', {
    input,
    use_vllm: useVllm,
    ...(chatHistory.length ? { chat_history: chatHistory } : {}),
    ...(trimmed ? { vector_store_id: trimmed } : {}),
  });
}
