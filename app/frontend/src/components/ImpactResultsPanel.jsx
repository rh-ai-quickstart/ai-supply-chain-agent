import PropTypes from "prop-types";
import { ChatMarkdownBody } from "./ChatMarkdownBody.jsx";
import { CollapsibleSection } from "./CollapsibleSection.jsx";
import { SectionHeading } from "./SectionHeading.jsx";
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

function ImpactResultsHeading() {
  return (
    <SectionHeading tooltip="Impact score, affected entities, and recommended actions for the selected scenario.">
      Impact Results
    </SectionHeading>
  );
}

export function ImpactResultsPanel({
  result = null,
  loading = false,
  onFocusEntity,
  onFocusDiversion,
  focusedDiversionKey = "",
}) {
  if (loading) {
    return (
      <section className="panel impact-results-panel" role="status" aria-live="polite">
        <ImpactResultsHeading />
        <div className="loading-spinner-container">
          <div className="loading-spinner" aria-hidden="true"></div>
          <p className="muted loading-spinner-label">Analyzing impact…</p>
        </div>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="panel impact-results-panel">
        <ImpactResultsHeading />
        <p className="muted">Select a scenario to see impact score, value at risk, and response options.</p>
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
      <ImpactResultsHeading />

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

      <div className="impact-results-sections">
        {answer ? (
          <CollapsibleSection
            title="Answer"
            tooltip="Natural-language summary from the impact analysis agent for this scenario."
          >
            <ChatMarkdownBody content={answer} compact />
          </CollapsibleSection>
        ) : null}

        {options.length > 0 ? (
          <CollapsibleSection
            title={`Response options (${options.length})`}
            tooltipLabel="About response options"
            tooltip="Ranked mitigation strategies with estimated impact reduction for each option."
          >
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
          </CollapsibleSection>
        ) : null}

        {reroutes.length > 0 ? (
          <CollapsibleSection
            title={`Recommended diversions (${reroutes.length})`}
            tooltipLabel="About recommended diversions"
            tooltip="Suggested alternate routes for affected entities. Click a diversion to highlight it on the map."
          >
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
          </CollapsibleSection>
        ) : null}

        {breakdown.length > 0 ? (
          <CollapsibleSection
            title={`Value breakdown (${breakdown.length})`}
            tooltipLabel="About value breakdown"
            tooltip="Per-entity financial exposure. Aircraft rows are flight revenue; cargo rows are shipment value on board."
          >
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
          </CollapsibleSection>
        ) : null}

        {affected.length > 0 ? (
          <CollapsibleSection
            title={`Affected entities (${affected.length})`}
            tooltipLabel="About affected entities"
            tooltip="Flights, vessels, and facilities impacted by the disruption. Click an entity to focus it on the map."
          >
            <ul className="impact-entity-link-list">
              {affected.map((entityId) => (
                <li key={entityId}>
                  <EntityLink entityId={entityId} onFocusEntity={onFocusEntity} />
                </li>
              ))}
            </ul>
          </CollapsibleSection>
        ) : null}

        {trace.length > 0 ? (
          <CollapsibleSection
            title={`Tool call trace (${trace.length})`}
            className="impact-trace"
            tooltipLabel="About tool call trace"
            tooltip="Debug log of tools the agent called while building this result, including inputs and outputs."
          >
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
          </CollapsibleSection>
        ) : null}
      </div>
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
