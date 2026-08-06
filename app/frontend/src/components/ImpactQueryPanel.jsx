import PropTypes from "prop-types";
import { DEFAULT_IMPACT_QUESTION, labelForScenario } from "../services/presetScenarioIds";

export { DEFAULT_IMPACT_QUESTION };

export function ImpactQueryPanel({
  scenarios = [],
  scenariosLoading = false,
  scenariosError = "",
  scenarioId = "",
  onChangeScenarioId,
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
  question: PropTypes.string,
  onChangeQuestion: PropTypes.func,
  onRunQuery: PropTypes.func,
  queryLoading: PropTypes.bool,
  chatBusy: PropTypes.bool,
  queryError: PropTypes.string,
};
