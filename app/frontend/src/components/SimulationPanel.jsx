import { useState } from "react";
import PropTypes from "prop-types";

function findVectorStoreId(stores, keywords) {
  for (const store of stores) {
    const name = (store.name || "").toLowerCase();
    if (keywords.some((kw) => name.includes(kw))) {
      return store.id;
    }
  }
  return "";
}

const SCENARIO_KEYWORDS = {
  "port-strike": ["port", "strike", "land"],
  geopolitical: ["suez", "geopolitical"],
  none: [],
};

export function SimulationPanel({
  mapView = "airFreight",
  optimize = false,
  onOptimizeChange: _onOptimizeChange,
  onRunScenario,
  onTriggerEvent,
  simulationLoading = false,
  simulationError = "",
  vectorStores = [],
  setSelectedVectorStoreId,
}) {
  const [activeScenario, setActiveScenario] = useState("");

  const handleRun = (scenario) => {
    setActiveScenario(scenario);
    const keywords = SCENARIO_KEYWORDS[scenario] || [];
    const storeId = keywords.length > 0 ? findVectorStoreId(vectorStores, keywords) : "";
    setSelectedVectorStoreId(storeId);
    onRunScenario({ scenario, optimize });
  };

  const handleTriggerWorld = () => {
    setActiveScenario("world-event");
    const storeId = findVectorStoreId(vectorStores, ["air", "risk", "iceland"]);
    setSelectedVectorStoreId(storeId);
    onTriggerEvent(mapView);
  };

  return (
    <section className="panel">
      <h3>AI Simulation & Presets</h3>

      <label className="field-label">Scenario Presets</label>
      <div className="stack">
        <button
          className={`btn${activeScenario === "none" ? " btn--active" : ""}`}
          onClick={() => handleRun("none")}
          disabled={simulationLoading}
        >
          Live Dashboard
        </button>
        <button
          className={`btn${activeScenario === "port-strike" ? " btn--active" : ""}`}
          onClick={() => handleRun("port-strike")}
          disabled={simulationLoading}
        >
          Port Strike LA
        </button>
        <button
          className={`btn${activeScenario === "geopolitical" ? " btn--active" : ""}`}
          onClick={() => handleRun("geopolitical")}
          disabled={simulationLoading}
        >
          Suez Blockage
        </button>
        <button
          className={`btn${activeScenario === "world-event" ? " btn--active" : ""}`}
          onClick={handleTriggerWorld}
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

SimulationPanel.propTypes = {
  mapView: PropTypes.string,
  optimize: PropTypes.bool,
  onOptimizeChange: PropTypes.func,
  onRunScenario: PropTypes.func,
  onTriggerEvent: PropTypes.func,
  simulationLoading: PropTypes.bool,
  simulationError: PropTypes.string,
  vectorStores: PropTypes.array,
  setSelectedVectorStoreId: PropTypes.func,
};
