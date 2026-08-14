import PropTypes from "prop-types";
import { useCallback } from "react";
import { ImpactMapPanel } from "./ImpactMapPanel";
import { ImpactQueryPanel } from "./ImpactQueryPanel";
import { ImpactResultsPanel } from "./ImpactResultsPanel";
import { useImpactSimulation } from "../hooks/useImpactSimulation";

export function ImpactSimulationPage({
  initialScenarioId = "",
  onScenarioChange,
  onOpenCreateScenario,
  chatSimulation = null,
  chatLoading = false,
  onSendPrompt,
}) {
  const sim = useImpactSimulation({
    initialScenarioId,
    onScenarioChange,
    chatSimulation,
    chatLoading,
  });

  const handleRunSuggestedPrompt = useCallback(
    (prompt) => {
      sim.setQuestion(prompt);
      if (onSendPrompt) {
        onSendPrompt(prompt);
      } else {
        sim.handleRunSuggestedPrompt(prompt);
      }
    },
    [onSendPrompt, sim],
  );

  const handleOpenCreateScenario = useCallback(() => {
    onOpenCreateScenario?.();
  }, [onOpenCreateScenario]);

  return (
    <main className="dashboard-grid impact-simulation-grid">
      <ImpactQueryPanel
        scenarios={sim.scenarios}
        scenariosLoading={sim.scenariosLoading}
        scenariosError={sim.scenariosError}
        scenarioId={sim.scenarioId}
        onChangeScenarioId={sim.handleChangeScenarioId}
        mapMode={sim.mapMode}
        onChangeMapMode={sim.handleMapModeChange}
        onRunSuggestedPrompt={handleRunSuggestedPrompt}
        onCreateScenario={handleOpenCreateScenario}
        queryLoading={sim.queryLoading}
        chatBusy={chatLoading}
        queryError={sim.queryError}
      />

      <section className="center-content">
        <ImpactMapPanel
          title={sim.mapTitle}
          features={sim.collection.features}
          focusBbox={sim.focusBbox}
          highlightedIds={sim.highlightedIds}
          reroutes={sim.reroutes}
          focusedEntityId={sim.focusedEntityId}
          focusNonce={sim.focusNonce}
          selectedDiversionKey={sim.selectedDiversionKey}
          diversionFocusNonce={sim.diversionFocusNonce}
          valueByEntity={sim.valueByEntity}
          currency={sim.currency}
          loading={sim.mapLoading}
          error={sim.mapError}
          warning={sim.mapWarning}
        />
      </section>

      <ImpactResultsPanel
        result={sim.result}
        loading={sim.queryLoading}
        onFocusEntity={sim.handleFocusEntity}
        onFocusDiversion={sim.handleFocusDiversion}
        focusedDiversionKey={sim.selectedDiversionKey}
      />
    </main>
  );
}

ImpactSimulationPage.propTypes = {
  initialScenarioId: PropTypes.string,
  onScenarioChange: PropTypes.func,
  onOpenCreateScenario: PropTypes.func,
  chatSimulation: PropTypes.object,
  chatLoading: PropTypes.bool,
  onSendPrompt: PropTypes.func,
};
