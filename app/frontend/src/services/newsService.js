import { apiGet } from "./apiClient";

export function getNews({ signal, limit = 30 } = {}) {
  const capped = Math.max(1, Math.min(Number(limit) || 30, 50));
  return apiGet(`/api/v1/news?limit=${capped}`, { signal });
}
