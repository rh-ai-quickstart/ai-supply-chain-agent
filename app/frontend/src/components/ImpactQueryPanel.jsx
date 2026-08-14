import PropTypes from "prop-types";
import { Plus } from "lucide-react";
import { InfoTooltip } from "./InfoTooltip";
import { SectionHeading } from "./SectionHeading";
import { labelForScenario, suggestedPromptsForScenario } from "../services/presetScenarioIds";

export function ImpactQueryPanel({
  scenarios = [],
  scenariosLoading = false,
  scenariosError = "",
  scenarioId = "",
  onChangeScenarioId,
  mapMode = "live",
  onChangeMapMode,
  onRunSuggestedPrompt,
  onCreateScenario,
  queryLoading = false,
  chatBusy = false,
  queryError = "",
}) {
  const locked = queryLoading || chatBusy;
  const suggestedPrompts = suggestedPromptsForScenario(scenarioId);
  const showStatus = queryLoading || (chatBusy && !queryLoading) || Boolean(queryError);

  return (
    <section className="panel impact-query-panel">
      <div className="impact-query-panel__scroll">
        <span className="field-label field-label--with-hint" id="impact-map-mode-label">
          Map view
          <InfoTooltip
            label="About map view"
            content="All Flights shows the full demo map. Scenario focus zooms to the selected scenario region."
          />
        </span>
        <div className="impact-map-mode" role="group" aria-labelledby="impact-map-mode-label">
          <button
            type="button"
            className={`btn${mapMode === "live" ? " btn--active" : ""}`}
            onClick={() => onChangeMapMode?.("live")}
            aria-pressed={mapMode === "live"}
            title="Show all demo flight entities on the map"
          >
            All Flights
          </button>
          <button
            type="button"
            className={`btn${mapMode === "scenario" ? " btn--active" : ""}`}
            onClick={() => onChangeMapMode?.("scenario")}
            disabled={!scenarioId.trim()}
            aria-pressed={mapMode === "scenario"}
            title="Frame the map on the active scenario region"
          >
            Scenario focus
          </button>
        </div>

        <div className="impact-query-panel__scenario-heading">
          <h3>Scenario Selection</h3>
          <InfoTooltip
            label="About scenario selection"
            content="Choose a disruption scenario to run impact analysis. Selecting a scenario updates the map, results, and chat knowledge base."
          />
          <button
            type="button"
            className="impact-create-scenario-btn"
            onClick={onCreateScenario}
            aria-label="Create scenario"
            title="Create a custom disruption scenario with AI assistance"
          >
            <Plus size={16} aria-hidden="true" />
          </button>
        </div>

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
                title={`Run ${labelForScenario(id)} and update impact analysis`}
              >
                {labelForScenario(id)}
              </button>
            ))}
          </div>
        )}
        {scenariosError ? <p className="error">{scenariosError}</p> : null}

        {suggestedPrompts.length > 0 ? (
          <div className="stack impact-suggested-prompts">
            <SectionHeading
              id="impact-suggested-prompt-label"
              tooltip="Click a prompt to send it to the AI assistant and run impact analysis for the selected scenario."
            >
              Suggested prompts
            </SectionHeading>
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
                  title={`Send to AI assistant: ${prompt}`}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {showStatus ? (
        <div className="impact-query-panel__actions">
          {queryLoading ? <p className="muted">Running Scenario…</p> : null}
          {chatBusy && !queryLoading ? (
            <p className="muted">Chat in progress — map refresh and Scenario paused…</p>
          ) : null}
          {queryError ? <p className="error">{queryError}</p> : null}
        </div>
      ) : null}
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
  onRunSuggestedPrompt: PropTypes.func,
  onCreateScenario: PropTypes.func,
  queryLoading: PropTypes.bool,
  chatBusy: PropTypes.bool,
  queryError: PropTypes.string,
};
