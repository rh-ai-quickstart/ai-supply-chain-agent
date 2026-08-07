import { apiGet } from "./apiClient";

export function getNews({ signal, limit = 30 } = {}) {
  const parsed = Number(limit);
  const base = Number.isFinite(parsed) ? parsed : 30;
  const capped = Math.max(1, Math.min(base, 50));
  return apiGet(`/api/v1/news?limit=${capped}`, { signal });
}
