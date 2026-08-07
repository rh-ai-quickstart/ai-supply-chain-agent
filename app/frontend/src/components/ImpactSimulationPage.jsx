import PropTypes from "prop-types";
import { ImpactMapPanel } from "./ImpactMapPanel";
import { ImpactQueryPanel } from "./ImpactQueryPanel";
import { ImpactResultsPanel } from "./ImpactResultsPanel";
import { useImpactSimulation } from "../hooks/useImpactSimulation";

export function ImpactSimulationPage({
  initialScenarioId = "",
  onScenarioChange,
  chatSimulation = null,
  chatLoading = false,
}) {
  const sim = useImpactSimulation({
    initialScenarioId,
    onScenarioChange,
    chatSimulation,
    chatLoading,
  });

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
        question={sim.question}
        onChangeQuestion={sim.setQuestion}
        onRunQuery={sim.handleRunQuery}
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
  chatSimulation: PropTypes.object,
  chatLoading: PropTypes.bool,
};
