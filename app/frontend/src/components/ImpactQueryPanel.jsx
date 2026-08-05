import PropTypes from "prop-types";

export const DEFAULT_IMPACT_QUESTION =
  "UK airspace is closed due to a NATS GPS failure. Which aircraft are affected, what diversions should be issued, and what is the estimated cost of impact?";

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
  queryError = "",
}) {
  const canRun = Boolean(scenarioId.trim()) && Boolean(question.trim()) && !queryLoading;

  return (
    <section className="panel impact-query-panel">
      <h3>Impact Query</h3>

      <label className="field-label" htmlFor="impact-scenario">
        Scenario
      </label>
      {scenariosLoading ? (
        <p className="muted">Loading scenarios…</p>
      ) : (
        <select
          id="impact-scenario"
          className="impact-select"
          value={scenarioId}
          onChange={(event) => onChangeScenarioId(event.target.value)}
          disabled={queryLoading || scenarios.length === 0}
        >
          {scenarios.length === 0 ? (
            <option value="">No scenarios available</option>
          ) : (
            scenarios.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))
          )}
        </select>
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
        disabled={queryLoading}
      />

      <div className="stack">
        <button className="btn" type="button" onClick={onRunQuery} disabled={!canRun}>
          Run impact query
        </button>
      </div>
      {queryLoading ? <p className="muted">Running impact query…</p> : null}
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
  queryError: PropTypes.string,
};
