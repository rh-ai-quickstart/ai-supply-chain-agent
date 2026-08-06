import { useCallback, useState } from "react";
import { createScenario, proposeScenario } from "../services/scenarioCreateService";

const EMPTY_DRAFT = {
  name: "",
  scenario_id: "",
  description: "",
  affect_bbox: "",
  place_summary: "",
  rationale: "",
};

/**
 * Propose/create scenario-draft workflow, extracted from `CreateScenarioPage.jsx`
 * (SRP). The page component stays responsible only for the form markup.
 */
export function useCreateScenario(onCreated) {
  const [prompt, setPrompt] = useState("");
  const [draft, setDraft] = useState(null);
  const [proposing, setProposing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const locked = proposing || creating;

  const propose = useCallback(async () => {
    const text = prompt.trim();
    if (!text || locked) return;
    setError("");
    setProposing(true);
    try {
      const result = await proposeScenario(text);
      if (!result?.success || !result.draft) {
        setError(result?.error || "Unable to propose a scenario.");
        setDraft(null);
        return;
      }
      setDraft({ ...EMPTY_DRAFT, ...result.draft });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to propose a scenario.");
      setDraft(null);
    } finally {
      setProposing(false);
    }
  }, [prompt, locked]);

  const updateDraftField = useCallback((key, value) => {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  }, []);

  const create = useCallback(async () => {
    if (!draft || locked) return;
    setError("");
    setCreating(true);
    try {
      const result = await createScenario(draft);
      if (!result?.success || !result.scenario_id) {
        setError(result?.error || "Unable to create scenario.");
        return;
      }
      onCreated?.(result.scenario_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create scenario.");
    } finally {
      setCreating(false);
    }
  }, [draft, locked, onCreated]);

  return {
    prompt,
    setPrompt,
    draft,
    proposing,
    creating,
    error,
    locked,
    propose,
    updateDraftField,
    create,
  };
}
