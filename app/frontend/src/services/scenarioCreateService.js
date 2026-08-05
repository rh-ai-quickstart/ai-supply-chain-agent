import { apiPost } from "./apiClient";

/**
 * Ask the backend LLM to draft a general-simulation scenario from natural language.
 * @param {string} prompt
 * @returns {Promise<{ success: boolean, draft?: object, error?: string }>}
 */
export async function proposeScenario(prompt, { signal } = {}) {
  return apiPost("/api/v1/scenarios/propose", { prompt }, { signal });
}

/**
 * Persist a confirmed scenario draft into general-simulation.
 * @param {object} draft
 * @returns {Promise<{ success: boolean, scenario_id?: string, error?: string }>}
 */
export async function createScenario(draft, { signal } = {}) {
  return apiPost("/api/v1/scenarios", draft, { signal });
}
