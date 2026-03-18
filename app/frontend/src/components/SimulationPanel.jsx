import { useState } from "react";

export function SimulationPanel({
  mapView,
  onRunScenario,
  onTriggerEvent,
  simulationLoading,
  simulationError,
}) {
  const [optimize, setOptimize] = useState(false);

  const handleRun = (scenario) => {
    onRunScenario({ scenario, optimize });
  };

  return (
    <section className="panel">
      <h3>AI Simulation & Presets</h3>
      <label className="field-label">Infrastructure Engine</label>
      <label className="row checkbox-row">
        <input
          type="checkbox"
          checked={optimize}
          onChange={(event) => setOptimize(event.target.checked)}
        />
        Enable vLLM & LLM-D
      </label>

      <label className="field-label">Scenario Presets</label>
      <div className="stack">
        <button className="btn" onClick={() => handleRun("none")} disabled={simulationLoading}>
          Live Dashboard
        </button>
        <button
          className="btn"
          onClick={() => handleRun("port-strike")}
          disabled={simulationLoading}
        >
          Port Strike LA
        </button>
        <button
          className="btn"
          onClick={() => handleRun("geopolitical")}
          disabled={simulationLoading}
        >
          Suez Blockage
        </button>
        <button
          className="btn"
          onClick={() => onTriggerEvent(mapView)}
          disabled={simulationLoading}
        >
          Trigger World Event
        </button>
      </div>
      {simulationLoading && <p className="muted">Running simulation...</p>}
      {simulationError && <p className="error">{simulationError}</p>}
    </section>
  );
}
