import { apiGet } from "./apiClient";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);

export function getNews({ signal, limit = 30 } = {}) {
  const parsed = Number(limit);
  const base = Number.isFinite(parsed) ? parsed : 30;
  const capped = Math.max(1, Math.min(base, 50));
  logger.info("getNews: limit=%d", capped);
  return apiGet(`/api/v1/news?limit=${capped}`, { signal }).catch((err) => {
    logger.error("getNews error: %s", err.message);
    throw err;
  });
}
