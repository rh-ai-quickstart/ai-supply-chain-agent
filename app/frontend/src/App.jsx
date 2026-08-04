import { useCallback, useEffect, useMemo, useState } from "react";
import { applyChatStreamEvent } from "./utils/chatStream.js";
import { AlertsPanel } from "./components/AlertsPanel";
import { ChatBar } from "./components/ChatBar";
import { DashboardHeader } from "./components/DashboardHeader";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { KnowledgeBasesPage } from "./components/KnowledgeBasesPage";
import { KpiBar } from "./components/KpiBar";
import { LogisticsMapPanel } from "./components/LogisticsMapPanel";
import { SimulationPanel } from "./components/SimulationPanel";
import { useDashboardState } from "./hooks/useDashboardState";
import {
  getAssetCounts,
  getFlattenedAlerts,
  getKpis,
  getSelectedMapData,
} from "./services/dashboardMappers";
import {
  getVectorStores,
  runSimulation,
  sendChatMessageStream,
  triggerWorldEvent,
} from "./services/dashboardService";

function viewFromHash() {
  const raw = window.location.hash.replace(/^#/, "");
  if (raw === "/knowledge-bases" || raw === "knowledge-bases") {
    return "knowledge-bases";
  }
  if (raw === "/simulation" || raw === "simulation") {
    return "simulation";
  }
  return "dashboard";
}

function App() {
  const [isLightTheme, setIsLightTheme] = useState(false);
  const [optimize, setOptimize] = useState(false);
  const [mapView, setMapView] = useState("airFreight");
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [vectorStores, setVectorStores] = useState([]);
  const [_vectorStoresLoading, setVectorStoresLoading] = useState(false);
  const [_vectorStoresError, setVectorStoresError] = useState("");
  const [selectedVectorStoreId, setSelectedVectorStoreId] = useState("");
  const [activeView, setActiveView] = useState(viewFromHash);
  const { dashboardState, loading, error, setDashboardState } = useDashboardState();

  const reloadVectorStores = useCallback(async (signal) => {
    setVectorStoresLoading(true);
    setVectorStoresError("");
    try {
      const res = await getVectorStores({ signal });
      if (signal?.aborted) return;
      setVectorStores(Array.isArray(res.vector_stores) ? res.vector_stores : []);
      if (res.error) {
        setVectorStoresError(res.error);
      }
    } catch (err) {
      if (err?.name === "AbortError") return;
      setVectorStoresError("Unable to load vector stores from LlamaStack.");
      setVectorStores([]);
    } finally {
      if (!signal?.aborted) {
        setVectorStoresLoading(false);
      }
    }
  }, []);

   
  useEffect(() => {
    const controller = new AbortController();
    reloadVectorStores(controller.signal);
    return () => controller.abort();
  }, [reloadVectorStores]);

  useEffect(() => {
    const onHashChange = () => setActiveView(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (view) => {
    if (view === "knowledge-bases") {
      window.location.hash = "#/knowledge-bases";
    } else if (view === "simulation") {
      window.location.hash = "#/simulation";
    } else {
      window.location.hash = "#/";
    }
  };

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

    const humanMessage = { role: "human", content: question };
    const historyForApi = [...chatMessages, humanMessage];
    const aiPlaceholder = { role: "ai", content: "", completion: null };

    setChatMessages([...historyForApi, aiPlaceholder]);
    setChatInput("");
    setChatError("");
    setChatLoading(true);
    try {
      await sendChatMessageStream(
        question,
        historyForApi,
        selectedVectorStoreId.trim() || undefined,
        optimize,
        (event) => {
          setChatMessages((prev) => applyChatStreamEvent(prev, event) ?? prev);
        },
      );
    } catch {
      setChatError("Failed to send chat request.");
      setChatMessages(historyForApi);
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

  return (
    <div className={`dashboard-root ${isLightTheme ? "light-theme" : ""}`}>
      <ErrorBoundary>
      <div
        className={`dashboard-wrapper${activeView === "knowledge-bases" ? " dashboard-wrapper--kb" : ""}`}
      >
        <DashboardHeader
          isLightTheme={isLightTheme}
          onToggleTheme={() => setIsLightTheme((value) => !value)}
          activeView={activeView}
          onNavigate={navigate}
        />

        {activeView === "simulation" ? (
          <SimulationPanel
            mapView={mapView}
            optimize={optimize}
            onOptimizeChange={setOptimize}
            onRunScenario={handleRunScenario}
            onTriggerEvent={handleTriggerEvent}
            simulationLoading={simulationLoading}
            simulationError={simulationError}
            vectorStores={vectorStores}
            setSelectedVectorStoreId={setSelectedVectorStoreId}
          />
        ) : activeView === "dashboard" ? (
          <>
            <KpiBar kpis={kpis} />

            <main className="dashboard-grid">
              <SimulationPanel
                mapView={mapView}
                optimize={optimize}
                onOptimizeChange={setOptimize}
                onRunScenario={handleRunScenario}
                onTriggerEvent={handleTriggerEvent}
                simulationLoading={simulationLoading}
                simulationError={simulationError}
                vectorStores={vectorStores}
                setSelectedVectorStoreId={setSelectedVectorStoreId}
              />

              <section className="center-content">
                <LogisticsMapPanel
                  mapView={mapView}
                  onChangeMapView={setMapView}
                  selectedMapData={selectedMapData}
                  assetCounts={assetCounts}
                />
              </section>

              <AlertsPanel loading={loading} error={error} alerts={alerts} />
            </main>

            <ChatBar
              chatInput={chatInput}
              onChangeChatInput={setChatInput}
              onSubmitChat={handleSubmitChat}
              chatLoading={chatLoading}
              chatError={chatError}
              chatMessages={chatMessages}
            />
          </>
        ) : (
          <KnowledgeBasesPage onKnowledgeBaseCreated={reloadVectorStores} />
        )}
      </div>
      </ErrorBoundary>
    </div>
  );
}

export default App;
