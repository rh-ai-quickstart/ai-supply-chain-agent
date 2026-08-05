import PropTypes from "prop-types";
import { ChatMarkdownBody } from "./ChatMarkdownBody.jsx";

function formatCurrency(amount, currency = "USD") {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return `${currency} —`;
  }
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  }
}

function formatScore(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return "—";
  return value.toFixed(3);
}

export function ImpactResultsPanel({ result = null, loading = false }) {
  if (loading) {
    return (
      <section className="panel impact-results-panel">
        <h3>Impact Results</h3>
        <p className="muted">Waiting for solver response…</p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="panel impact-results-panel">
        <h3>Impact Results</h3>
        <p className="muted">Run a query to see impact score, value at risk, and response options.</p>
      </section>
    );
  }

  const solver = result.solver || {};
  const currency = solver.currency || "USD";
  const breakdown = Array.isArray(solver.value_breakdown) ? solver.value_breakdown : [];
  const options = Array.isArray(solver.response_options) ? solver.response_options : [];
  const trace = Array.isArray(result.tool_call_trace) ? result.tool_call_trace : [];
  const affected = Array.isArray(result.affected_entities) ? result.affected_entities : [];

  return (
    <section className="panel impact-results-panel insights-panel">
      <h3>Impact Results</h3>

      <div className="impact-kpi-strip">
        <div className="kpi-card">
          <span className="kpi-label">Impact score</span>
          <span className="kpi-value">{formatScore(solver.impact_score)}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Value at risk</span>
          <span className="kpi-value">
            {formatCurrency(solver.total_value_at_risk, currency)}
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Affected</span>
          <span className="kpi-value">{solver.affected_count ?? affected.length ?? "—"}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Max chain</span>
          <span className="kpi-value">{solver.max_chain_length ?? "—"}</span>
        </div>
      </div>

      {result.answer ? (
        <div className="impact-answer">
          <h4 className="impact-section-title">Answer</h4>
          <ChatMarkdownBody content={result.answer} compact />
        </div>
      ) : null}

      {options.length > 0 ? (
        <div className="impact-section">
          <h4 className="impact-section-title">Response options</h4>
          <ul className="impact-list">
            {options.map((opt) => (
              <li key={`${opt.rank}-${opt.label}`} className="alert info">
                <strong>
                  #{opt.rank} {opt.label}
                </strong>
                {opt.description ? ` — ${opt.description}` : ""}
                {opt.estimated_impact_reduction != null ? (
                  <em className="muted">
                    {" "}
                    (Δ impact ≈ {Number(opt.estimated_impact_reduction).toFixed(3)})
                  </em>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {breakdown.length > 0 ? (
        <div className="impact-section">
          <h4 className="impact-section-title">Value breakdown</h4>
          <ul className="impact-list">
            {breakdown.map((row) => (
              <li key={row.entity_id}>
                <strong>{row.entity_id}</strong> — {formatCurrency(row.value_usd, currency)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {affected.length > 0 ? (
        <div className="impact-section">
          <h4 className="impact-section-title">Affected entities ({affected.length})</h4>
          <p className="muted impact-entity-ids">{affected.join(", ")}</p>
        </div>
      ) : null}

      {trace.length > 0 ? (
        <details className="impact-trace">
          <summary>Tool call trace ({trace.length})</summary>
          <ul className="impact-list">
            {trace.map((step, index) => (
              <li key={`${step.tool_name}-${index}`}>
                <strong>{step.tool_name}</strong>
                <pre className="impact-trace-pre">
                  {JSON.stringify(
                    { arguments: step.arguments, output: step.output },
                    null,
                    2,
                  )}
                </pre>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}

ImpactResultsPanel.propTypes = {
  result: PropTypes.shape({
    answer: PropTypes.string,
    affected_entities: PropTypes.arrayOf(PropTypes.string),
    solver: PropTypes.object,
    tool_call_trace: PropTypes.array,
  }),
  loading: PropTypes.bool,
};
