import { apiGet, apiPost } from "./apiClient";

export function runImpactQuery({ question, scenarioId }) {
  return apiPost("/api/v1/general-simulation/query", {
    question,
    scenario_id: scenarioId,
  });
}

export function listImpactScenarios({ signal } = {}) {
  return apiGet("/api/v1/general-simulation/scenarios", { signal });
}

export function getImpactEntitiesGeoJson({ bbox, ids, limit, signal } = {}) {
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
