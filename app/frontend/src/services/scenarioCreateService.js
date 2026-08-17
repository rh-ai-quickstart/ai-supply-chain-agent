import { apiPost } from "./apiClient";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);

/**
 * Ask the backend LLM to draft a general-simulation scenario from natural language.
 * @param {string} prompt
 * @returns {Promise<{ success: boolean, draft?: object, error?: string }>}
 */
export async function proposeScenario(prompt, { signal } = {}) {
  logger.info("proposeScenario: %s", (prompt || "").slice(0, 80));
  try {
    return await apiPost("/api/v1/scenarios/propose", { prompt }, { signal });
  } catch (err) {
    logger.error("proposeScenario error: %s", err.message);
    throw err;
  }
}

/**
 * Persist a confirmed scenario draft into general-simulation.
 * @param {object} draft
 * @returns {Promise<{ success: boolean, scenario_id?: string, error?: string }>}
 */
export async function createScenario(draft, { signal } = {}) {
  const scenarioId = draft?.scenario_id || "(unnamed)";
  logger.info("createScenario: scenario=%s", scenarioId);
  try {
    return await apiPost("/api/v1/scenarios", draft, { signal });
  } catch (err) {
    logger.error("createScenario error: %s", err.message);
    throw err;
  }
}
