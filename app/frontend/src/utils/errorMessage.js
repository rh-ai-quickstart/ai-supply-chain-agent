/**
 * Shared error-to-user-message mapping. Consolidates the ad hoc
 * `err instanceof Error ? err.message : ...` / AbortError-swallowing logic
 * that was duplicated across `ImpactSimulationPage`, `KnowledgeBasesPage`,
 * and `CreateScenarioModal`.
 */

/** True when `err` is a `fetch`/`AbortController` cancellation, not a real failure. */
export function isAbortError(err) {
  return err?.name === "AbortError";
}

/**
 * Map a caught error to a user-facing message, falling back to `fallback`.
 * Returns `""` for abort errors so callers can skip showing anything.
 * @param {unknown} err
 * @param {string} fallback
 */
export function messageFromError(err, fallback) {
  if (isAbortError(err)) return "";
  const msg = err instanceof Error ? err.message.trim() : "";
  return msg || fallback;
}
