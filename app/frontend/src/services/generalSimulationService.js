import { apiGet, apiPost } from "./apiClient";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);

export function runImpactQuery({ question, scenarioId }) {
  logger.info("runImpactQuery: scenario=%s question=%s", scenarioId, question.slice(0, 80));
  return apiPost("/api/v1/general-simulation/query", {
    question,
    scenario_id: scenarioId,
  }).catch((err) => {
    logger.error("runImpactQuery error: %s", err.message);
    throw err;
  });
}

export function listImpactScenarios({ signal } = {}) {
  logger.info("listImpactScenarios");
  return apiGet("/api/v1/general-simulation/scenarios", { signal });
}

export function getImpactEntitiesGeoJson({ bbox, ids, limit, signal } = {}) {
  logger.info("getImpactEntitiesGeoJson: bbox=%s ids=%d limit=%s", bbox, ids?.length || 0, limit);
  const params = new URLSearchParams();
  if (bbox) params.set("bbox", bbox);
  if (ids?.length) params.set("ids", ids.join(","));
  if (limit != null) params.set("limit", String(limit));
  const qs = params.toString();
  return apiGet(
    `/api/v1/general-simulation/entities/geojson${qs ? `?${qs}` : ""}`,
    { signal },
  );
}
