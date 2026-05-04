/**
 * HTTP client for `app/backend/api` (Flask) routes. Paths must stay in sync with `app/backend/api/main.py`.
 */
import type { DashboardState } from '../../types/dashboard';
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

/** Matches `ChatService.reply` — body is `{ input: string }` only. */
export function postAssistantMessage(input: string): Promise<{ answer?: string }> {
  return apiPost<{ answer?: string }>('/api/v1/chat', { input });
}
