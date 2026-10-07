import { apiGet, apiPost } from "./apiClient";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);

export function getSupplyChainKpis({ scenarioId, bbox, signal } = {}) {
  const params = new URLSearchParams();
  if (scenarioId) params.set("scenario_id", scenarioId);
  if (bbox) params.set("bbox", bbox);
  const qs = params.toString();
  logger.info("getSupplyChainKpis: scenario=%s bbox=%s", scenarioId || "", bbox || "");
  return apiGet(`/api/v1/kpis${qs ? `?${qs}` : ""}`, { signal });
}

export function postSupplyChainKpis(
  { scenarioId, bbox, solver, affectedEntities, signal } = {},
) {
  logger.info(
    "postSupplyChainKpis: scenario=%s affected=%d",
    scenarioId || "",
    affectedEntities?.length ?? 0,
  );
  return apiPost(
    "/api/v1/kpis",
    {
      scenario_id: scenarioId || "",
      bbox,
      solver,
      affected_entities: affectedEntities,
    },
    { signal },
  );
}
