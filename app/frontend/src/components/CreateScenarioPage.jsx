import PropTypes from "prop-types";
import { useState } from "react";
import { createScenario, proposeScenario } from "../services/scenarioCreateService";

const EMPTY_DRAFT = {
  name: "",
  scenario_id: "",
  description: "",
  affect_bbox: "",
  place_summary: "",
  rationale: "",
};

export function CreateScenarioPage({ onCreated }) {
  const [prompt, setPrompt] = useState("");
  const [draft, setDraft] = useState(null);
  const [proposing, setProposing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const locked = proposing || creating;

  const handlePropose = async (event) => {
    event.preventDefault();
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
  };

  const updateDraftField = (key, value) => {
    setDraft((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const handleCreate = async (event) => {
    event.preventDefault();
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
  };

  return (
    <div className="kb-page-root create-scenario-page">
      <section className="kb-card panel">
        <h2 className="kb-card-title">Create scenario</h2>
        <p className="kb-help muted">
          Describe a disruption in natural language. The assistant proposes a name, scenario id,
          description, and geographic bbox. Confirm to persist it in general-simulation so Impact
          Query can run against live entities in that area.
        </p>
        {error ? (
          <p className="kb-alert error" role="alert">
            {error}
          </p>
        ) : null}

        <form className="kb-form" onSubmit={handlePropose}>
          <label className="kb-label" htmlFor="scenario-prompt">
            Disruption description <span className="kb-required">*</span>
          </label>
          <textarea
            id="scenario-prompt"
            className="kb-input create-scenario-textarea"
            rows={5}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={locked}
            placeholder="e.g. France airspace is closed for 48 hours due to ATC outage"
          />
          <button className="kb-submit" type="submit" disabled={locked || !prompt.trim()}>
            {proposing ? "Proposing…" : "Propose scenario"}
          </button>
        </form>
      </section>

      {draft ? (
        <section className="kb-card panel">
          <h2 className="kb-card-title">Review draft</h2>
          {draft.rationale ? (
            <p className="kb-help muted">
              <strong>Rationale:</strong> {draft.rationale}
            </p>
          ) : null}
          <form className="kb-form" onSubmit={handleCreate}>
            <label className="kb-label" htmlFor="draft-name">
              Name
            </label>
            <input
              id="draft-name"
              className="kb-input"
              type="text"
              value={draft.name}
              onChange={(e) => updateDraftField("name", e.target.value)}
              disabled={locked}
            />

            <label className="kb-label" htmlFor="draft-scenario-id">
              Scenario id
            </label>
            <input
              id="draft-scenario-id"
              className="kb-input"
              type="text"
              value={draft.scenario_id}
              onChange={(e) => updateDraftField("scenario_id", e.target.value)}
              disabled={locked}
              autoComplete="off"
            />

            <label className="kb-label" htmlFor="draft-description">
              Description
            </label>
            <textarea
              id="draft-description"
              className="kb-input create-scenario-textarea"
              rows={4}
              value={draft.description}
              onChange={(e) => updateDraftField("description", e.target.value)}
              disabled={locked}
            />

            <label className="kb-label" htmlFor="draft-bbox">
              Affect bbox (minLon,minLat,maxLon,maxLat)
            </label>
            <input
              id="draft-bbox"
              className="kb-input"
              type="text"
              value={draft.affect_bbox}
              onChange={(e) => updateDraftField("affect_bbox", e.target.value)}
              disabled={locked}
              autoComplete="off"
            />

            <label className="kb-label" htmlFor="draft-place">
              Place summary
            </label>
            <input
              id="draft-place"
              className="kb-input"
              type="text"
              value={draft.place_summary || ""}
              onChange={(e) => updateDraftField("place_summary", e.target.value)}
              disabled={locked}
            />

            <button
              className="kb-submit"
              type="submit"
              disabled={
                locked ||
                !draft.name.trim() ||
                !draft.scenario_id.trim() ||
                !draft.description.trim() ||
                !draft.affect_bbox.trim()
              }
            >
              {creating ? "Creating…" : "Create scenario"}
            </button>
          </form>
        </section>
      ) : null}
    </div>
  );
}

CreateScenarioPage.propTypes = {
  onCreated: PropTypes.func,
};
