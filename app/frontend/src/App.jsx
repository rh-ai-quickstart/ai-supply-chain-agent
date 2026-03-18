import { useMemo, useState } from "react";
import "./lib/chartSetup";
import { AlertsPanel } from "./components/AlertsPanel";
import { ChatBar } from "./components/ChatBar";
import { DashboardHeader } from "./components/DashboardHeader";
import { DemandChartPanel } from "./components/DemandChartPanel";
import { KpiBar } from "./components/KpiBar";
import { LogisticsMapPanel } from "./components/LogisticsMapPanel";
import { RevenueChartPanel } from "./components/RevenueChartPanel";
import { SimulationPanel } from "./components/SimulationPanel";
import { SystemHealthPanel } from "./components/SystemHealthPanel";
import { useDashboardState } from "./hooks/useDashboardState";
import {
  getAssetCounts,
  getFlattenedAlerts,
  getKpis,
  getSelectedMapData,
  toDemandChartData,
  toRevenueChartData,
  toSystemHealthMetrics,
} from "./services/dashboardMappers";
import {
  runSimulation,
  sendChatMessage,
  triggerWorldEvent,
} from "./services/dashboardService";

function App() {
  const [isLightTheme, setIsLightTheme] = useState(false);
  const [mapView, setMapView] = useState("airFreight");
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const { dashboardState, loading, error, setDashboardState } = useDashboardState();

  const handleRunScenario = async ({ scenario, optimize }) => {
    setSimulationError("");
    setSimulationLoading(true);
    try {
      const result = await runSimulation({ scenario, optimize });
      setDashboardState(result);
    } catch {
      setSimulationError("Failed to run simulation.");
    } finally {
      setSimulationLoading(false);
    }
  };

  const handleTriggerEvent = async (selectedMapView) => {
    setSimulationError("");
    setSimulationLoading(true);
    try {
      const result = await triggerWorldEvent(selectedMapView);
      setDashboardState(result);
    } catch {
      setSimulationError("Failed to trigger event.");
    } finally {
      setSimulationLoading(false);
    }
  };

  const handleSubmitChat = async () => {
    const question = chatInput.trim();
    if (!question || chatLoading) {
      return;
    }

    const nextHistory = [...chatMessages, { role: "human", content: question }];
    setChatMessages(nextHistory);
    setChatInput("");
    setChatError("");
    setChatLoading(true);
    try {
      const result = await sendChatMessage(question, nextHistory);
      const answer = result?.answer ?? "No response from assistant.";
      setChatMessages((current) => [...current, { role: "ai", content: answer }]);
    } catch {
      setChatError("Failed to send chat request.");
    } finally {
      setChatLoading(false);
    }
  };

  const kpis = useMemo(() => getKpis(dashboardState), [dashboardState]);
  const alerts = useMemo(() => getFlattenedAlerts(dashboardState), [dashboardState]);
  const assetCounts = useMemo(() => getAssetCounts(dashboardState), [dashboardState]);
  const selectedMapData = useMemo(
    () => getSelectedMapData(dashboardState, mapView),
    [dashboardState, mapView]
  );
  const demandData = useMemo(() => toDemandChartData(dashboardState), [dashboardState]);
  const revenueData = useMemo(() => toRevenueChartData(dashboardState), [dashboardState]);
  const systemHealth = useMemo(
    () => toSystemHealthMetrics(kpis, alerts, loading, error),
    [kpis, alerts, loading, error]
  );

  return (
    <div className={`dashboard-root ${isLightTheme ? "light-theme" : ""}`}>
      <div className="dashboard-wrapper">
        <DashboardHeader
          isLightTheme={isLightTheme}
          onToggleTheme={() => setIsLightTheme((value) => !value)}
        />

        <main className="dashboard-grid">
          <SimulationPanel
            mapView={mapView}
            onRunScenario={handleRunScenario}
            onTriggerEvent={handleTriggerEvent}
            simulationLoading={simulationLoading}
            simulationError={simulationError}
          />

          <section className="center-content">
            <div className="top-charts-container">
              <DemandChartPanel data={demandData} />
              <RevenueChartPanel data={revenueData} />
              <SystemHealthPanel health={systemHealth} />
            </div>

            <LogisticsMapPanel
              mapView={mapView}
              onChangeMapView={setMapView}
              selectedMapData={selectedMapData}
              assetCounts={assetCounts}
            />
          </section>

          <AlertsPanel loading={loading} error={error} alerts={alerts} />
        </main>

        <KpiBar kpis={kpis} />
        <ChatBar
          chatInput={chatInput}
          onChangeChatInput={setChatInput}
          onSubmitChat={handleSubmitChat}
          chatLoading={chatLoading}
          chatError={chatError}
          chatMessages={chatMessages}
        />
      </div>
    </div>
  );
}

export default App;
