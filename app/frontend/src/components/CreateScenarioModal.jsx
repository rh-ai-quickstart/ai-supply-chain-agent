import PropTypes from "prop-types";
import { useEffect, useRef } from "react";
import { useCreateScenario } from "../hooks/useCreateScenario";

export function CreateScenarioModal({ onClose, onCreated, initialPrompt = "" }) {
  const scenario = useCreateScenario(onCreated);
  const { draft, locked, setPrompt } = scenario;
  const promptRef = useRef(null);
  const previouslyFocusedRef = useRef(null);

  useEffect(() => {
    setPrompt(initialPrompt || "");
  }, [initialPrompt, setPrompt]);

  useEffect(() => {
    previouslyFocusedRef.current = document.activeElement;
    const timer = window.setTimeout(() => promptRef.current?.focus(), 0);

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose?.();
      }
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", onKeyDown);
      const prior = previouslyFocusedRef.current;
      if (prior && typeof prior.focus === "function") {
        prior.focus();
      }
    };
  }, [onClose]);

  const handlePropose = (event) => {
    event.preventDefault();
    scenario.propose();
  };

  const handleCreate = (event) => {
    event.preventDefault();
    scenario.create();
  };

  return (
    <div
      className="chat-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-scenario-modal-title"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose?.();
        }
      }}
    >
      <div className="chat-modal-content create-scenario-modal">
        <div className="chat-modal-header">
          <h3 id="create-scenario-modal-title">Create scenario</h3>
          <button type="button" className="chat-modal-dismiss" onClick={onClose} aria-label="Close dialog">
            ×
          </button>
        </div>
        <div className="create-scenario-modal-body">
          <p className="kb-help muted">
            Describe a disruption in natural language. The assistant proposes a name, scenario id,
            description, and geographic bbox. Confirm to persist it in general-simulation so Impact
            Query can run against live entities in that area.
          </p>
          {scenario.error ? (
            <p className="kb-alert error" role="alert">
              {scenario.error}
            </p>
          ) : null}

          <form className="kb-form" onSubmit={handlePropose}>
            <label className="kb-label" htmlFor="scenario-prompt">
              Disruption description <span className="kb-required">*</span>
            </label>
            <textarea
              ref={promptRef}
              id="scenario-prompt"
              className="kb-input create-scenario-textarea"
              rows={5}
              value={scenario.prompt}
              onChange={(e) => scenario.setPrompt(e.target.value)}
              disabled={locked}
              placeholder="e.g. France airspace is closed for 48 hours due to ATC outage"
            />
            <button className="kb-submit" type="submit" disabled={locked || !scenario.prompt.trim()}>
              {scenario.proposing ? "Proposing…" : "Propose scenario"}
            </button>
          </form>

          {draft ? (
            <section className="create-scenario-draft">
              <h4 className="kb-card-title">Review draft</h4>
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
                  onChange={(e) => scenario.updateDraftField("name", e.target.value)}
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
                  onChange={(e) => scenario.updateDraftField("scenario_id", e.target.value)}
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
                  onChange={(e) => scenario.updateDraftField("description", e.target.value)}
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
                  onChange={(e) => scenario.updateDraftField("affect_bbox", e.target.value)}
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
                  onChange={(e) => scenario.updateDraftField("place_summary", e.target.value)}
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
                  {scenario.creating ? "Creating…" : "Create scenario"}
                </button>
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}

CreateScenarioModal.propTypes = {
  onClose: PropTypes.func,
  onCreated: PropTypes.func,
  initialPrompt: PropTypes.string,
};
