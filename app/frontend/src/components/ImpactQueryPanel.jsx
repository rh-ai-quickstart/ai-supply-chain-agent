import PropTypes from "prop-types";
import { labelForScenario, suggestedPromptsForScenario } from "../services/presetScenarioIds";

export function ImpactQueryPanel({
  scenarios = [],
  scenariosLoading = false,
  scenariosError = "",
  scenarioId = "",
  onChangeScenarioId,
  mapMode = "live",
  onChangeMapMode,
  question = "",
  onChangeQuestion,
  onRunQuery,
  onRunSuggestedPrompt,
  queryLoading = false,
  chatBusy = false,
  queryError = "",
}) {
  const locked = queryLoading || chatBusy;
  const canRun = Boolean(scenarioId.trim()) && Boolean(question.trim()) && !locked;
  const suggestedPrompts = suggestedPromptsForScenario(scenarioId);

  return (
    <section className="panel impact-query-panel">
      <div className="impact-query-panel__scroll">
        <span className="field-label" id="impact-map-mode-label">
          Map view
        </span>
        <div className="impact-map-mode" role="group" aria-labelledby="impact-map-mode-label">
          <button
            type="button"
            className={`btn${mapMode === "live" ? " btn--active" : ""}`}
            onClick={() => onChangeMapMode?.("live")}
            aria-pressed={mapMode === "live"}
          >
            All Flights
          </button>
          <button
            type="button"
            className={`btn${mapMode === "scenario" ? " btn--active" : ""}`}
            onClick={() => onChangeMapMode?.("scenario")}
            disabled={!scenarioId.trim()}
            aria-pressed={mapMode === "scenario"}
          >
            Scenario focus
          </button>
        </div>

        <h3>Scenario Selection</h3>

        <span className="field-label" id="impact-scenario-label">
          Scenario
        </span>
        {scenariosLoading ? (
          <p className="muted">Loading scenarios…</p>
        ) : scenarios.length === 0 ? (
          <p className="muted">No scenarios available</p>
        ) : (
          <div className="stack" role="group" aria-labelledby="impact-scenario-label">
            {scenarios.map((id) => (
              <button
                key={id}
                type="button"
                className={`btn${scenarioId === id ? " btn--active" : ""}`}
                onClick={() => onChangeScenarioId(id)}
                disabled={locked}
                aria-pressed={scenarioId === id}
              >
                {labelForScenario(id)}
              </button>
            ))}
          </div>
        )}
        {scenariosError ? <p className="error">{scenariosError}</p> : null}

        <label className="field-label" htmlFor="impact-question">
          Question
        </label>
        <textarea
          id="impact-question"
          className="impact-textarea"
          rows={8}
          value={question}
          onChange={(event) => onChangeQuestion(event.target.value)}
          disabled={locked}
        />

        {suggestedPrompts.length > 0 ? (
          <div className="stack">
            <span className="field-label" id="impact-suggested-prompt-label">
              Suggested prompts
            </span>
            <div
              className="stack"
              role="group"
              aria-labelledby="impact-suggested-prompt-label"
            >
              {suggestedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  className="btn impact-suggested-prompt"
                  onClick={() => onRunSuggestedPrompt?.(prompt)}
                  disabled={locked || !scenarioId.trim()}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="impact-query-panel__actions">
        <button className="btn" type="button" onClick={onRunQuery} disabled={!canRun}>
          Run Scenario
        </button>
        {queryLoading ? <p className="muted">Running Scenario…</p> : null}
        {chatBusy && !queryLoading ? (
          <p className="muted">Chat in progress — map refresh and Scenario paused…</p>
        ) : null}
        {queryError ? <p className="error">{queryError}</p> : null}
      </div>
    </section>
  );
}

ImpactQueryPanel.propTypes = {
  scenarios: PropTypes.arrayOf(PropTypes.string),
  scenariosLoading: PropTypes.bool,
  scenariosError: PropTypes.string,
  scenarioId: PropTypes.string,
  onChangeScenarioId: PropTypes.func,
  mapMode: PropTypes.oneOf(["live", "scenario"]),
  onChangeMapMode: PropTypes.func,
  question: PropTypes.string,
  onChangeQuestion: PropTypes.func,
  onRunQuery: PropTypes.func,
  onRunSuggestedPrompt: PropTypes.func,
  queryLoading: PropTypes.bool,
  chatBusy: PropTypes.bool,
  queryError: PropTypes.string,
};
