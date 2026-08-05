import PropTypes from "prop-types";
import { ChatMarkdownBody } from "./ChatMarkdownBody.jsx";
import { dedupeImpactAnswer, diversionKey, formatCurrency } from "../utils/impactEntityUtils";

function formatScore(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return "—";
  return value.toFixed(3);
}

function EntityLink({ entityId, onFocusEntity }) {
  return (
    <button
      type="button"
      className="impact-entity-link"
      onClick={() => onFocusEntity?.(entityId)}
      title={`Show ${entityId} on map`}
    >
      {entityId}
    </button>
  );
}

EntityLink.propTypes = {
  entityId: PropTypes.string.isRequired,
  onFocusEntity: PropTypes.func,
};

function DiversionRow({ route, isSelected, onFocusDiversion }) {
  const label = route.target_label || route.target_id || "alternate";
  const entityId = route.entity_id || "unknown";
  return (
    <li>
      <button
        type="button"
        className={`impact-diversion-btn${isSelected ? " is-selected" : ""}`}
        onClick={() => onFocusDiversion?.(route)}
        aria-pressed={isSelected}
        title={`Show diversion route for ${entityId} to ${label} on map`}
      >
        <span className="impact-diversion-route">
          <span className="impact-diversion-entity">{entityId}</span>
          <span aria-hidden="true"> → </span>
          <strong>{label}</strong>
        </span>
        {route.rationale ? <span className="muted impact-diversion-rationale">{route.rationale}</span> : null}
      </button>
    </li>
  );
}

DiversionRow.propTypes = {
  route: PropTypes.shape({
    entity_id: PropTypes.string,
    target_id: PropTypes.string,
    target_label: PropTypes.string,
    rationale: PropTypes.string,
  }).isRequired,
  isSelected: PropTypes.bool,
  onFocusDiversion: PropTypes.func,
};

export function ImpactResultsPanel({
  result = null,
  loading = false,
  onFocusEntity,
  onFocusDiversion,
  focusedDiversionKey = "",
}) {
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
  const reroutes = Array.isArray(solver.recommended_reroutes) ? solver.recommended_reroutes : [];
  const trace = Array.isArray(result.tool_call_trace) ? result.tool_call_trace : [];
  const affected = Array.isArray(result.affected_entities) ? result.affected_entities : [];
  const hasValueAtRisk = Number.isFinite(Number(solver.total_value_at_risk));
  const answer = dedupeImpactAnswer(result.answer, {
    hasReroutes: reroutes.length > 0,
    hasOptions: options.length > 0,
    hasValueAtRisk,
  });

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

      {answer ? (
        <div className="impact-answer">
          <h4 className="impact-section-title">Answer</h4>
          <ChatMarkdownBody content={answer} compact />
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

      {reroutes.length > 0 ? (
        <div className="impact-section">
          <h4 className="impact-section-title">Recommended Diversions</h4>
          <p className="muted impact-breakdown-hint">Select a diversion to show its route on the map.</p>
          <ul className="impact-list impact-diversion-list">
            {reroutes.map((route) => (
              <DiversionRow
                key={diversionKey(route)}
                route={route}
                isSelected={focusedDiversionKey === diversionKey(route)}
                onFocusDiversion={onFocusDiversion}
              />
            ))}
          </ul>
        </div>
      ) : null}

      {breakdown.length > 0 ? (
        <div className="impact-section">
          <h4 className="impact-section-title">Value breakdown</h4>
          <p className="muted impact-breakdown-hint">
            Aircraft rows are flight revenue; cargo-* rows are shipment value on board.
          </p>
          <ul className="impact-list">
            {breakdown.map((row) => {
              const isCargo = String(row.entity_id || "").startsWith("cargo-");
              return (
                <li key={row.entity_id}>
                  <EntityLink entityId={row.entity_id} onFocusEntity={onFocusEntity} />
                  <span className="muted">
                    {" "}
                    ({isCargo ? "cargo" : "flight"}) — {formatCurrency(row.value_usd, currency)}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {affected.length > 0 ? (
        <div className="impact-section">
          <h4 className="impact-section-title">Affected entities ({affected.length})</h4>
          <ul className="impact-entity-link-list">
            {affected.map((entityId) => (
              <li key={entityId}>
                <EntityLink entityId={entityId} onFocusEntity={onFocusEntity} />
              </li>
            ))}
          </ul>
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
  onFocusEntity: PropTypes.func,
  onFocusDiversion: PropTypes.func,
  focusedDiversionKey: PropTypes.string,
};
