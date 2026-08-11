import PropTypes from "prop-types";
import { labelForScenario } from "../services/presetScenarioIds";

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
  queryLoading = false,
  chatBusy = false,
  queryError = "",
}) {
  const locked = queryLoading || chatBusy;
  const canRun = Boolean(scenarioId.trim()) && Boolean(question.trim()) && !locked;

  return (
    <section className="panel impact-query-panel">
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
          Live Flights
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

      <h3>Impact Query</h3>

      <span className="field-label" id="impact-scenario-label">
        Scenario
      </span>
      {scenariosLoading ? (
        <p className="muted">Loading scenarios…</p>
      ) : scenarios.length === 0 ? (
        <p className="muted">No scenarios available</p>
      ) : (
        <div
          className="stack"
          role="group"
          aria-labelledby="impact-scenario-label"
        >
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

      <div className="stack">
        <button className="btn" type="button" onClick={onRunQuery} disabled={!canRun}>
          Run impact query
        </button>
      </div>
      {queryLoading ? <p className="muted">Running impact query…</p> : null}
      {chatBusy && !queryLoading ? (
        <p className="muted">Chat in progress — map refresh and impact query paused…</p>
      ) : null}
      {queryError ? <p className="error">{queryError}</p> : null}
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
  queryLoading: PropTypes.bool,
  chatBusy: PropTypes.bool,
  queryError: PropTypes.string,
};
