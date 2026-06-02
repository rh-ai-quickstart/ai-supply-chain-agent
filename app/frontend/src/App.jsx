import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./lib/chartSetup";
import { AlertsPanel } from "./components/AlertsPanel";
import { ChatBar } from "./components/ChatBar";
import { DashboardHeader } from "./components/DashboardHeader";
import { KnowledgeBasesPage } from "./components/KnowledgeBasesPage";
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
  getVectorStores,
  runSimulation,
  sendChatMessage,
  triggerWorldEvent,
} from "./services/dashboardService";
import { handleChatStreamEvent } from "./utils/handleChatStreamEvent";

function viewFromHash() {
  const raw = window.location.hash.replace(/^#/, "");
  if (raw === "/knowledge-bases" || raw === "knowledge-bases") {
    return "knowledge-bases";
  }
  return "dashboard";
}

function App() {
  const [isLightTheme, setIsLightTheme] = useState(false);
  const [mapView, setMapView] = useState("airFreight");
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [vectorStores, setVectorStores] = useState([]);
  const [vectorStoresLoading, setVectorStoresLoading] = useState(false);
  const [vectorStoresError, setVectorStoresError] = useState("");
  const [selectedVectorStoreId, setSelectedVectorStoreId] = useState("");
  const [activeView, setActiveView] = useState(viewFromHash);
  const chatAbortRef = useRef(null);
  const { dashboardState, loading, error, setDashboardState } = useDashboardState();

  const reloadVectorStores = useCallback(async () => {
    setVectorStoresLoading(true);
    setVectorStoresError("");
    try {
      const res = await getVectorStores();
      setVectorStores(Array.isArray(res.vector_stores) ? res.vector_stores : []);
      if (res.error) {
        setVectorStoresError(res.error);
      }
    } catch {
      setVectorStoresError("Unable to load vector stores from LlamaStack.");
      setVectorStores([]);
    } finally {
      setVectorStoresLoading(false);
    }
  }, []);

  useEffect(() => {
    void reloadVectorStores();
  }, [reloadVectorStores]);

  useEffect(() => {
    const onHashChange = () => setActiveView(viewFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (view) => {
    window.location.hash = view === "knowledge-bases" ? "#/knowledge-bases" : "#/";
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

    chatAbortRef.current?.abort();
    const abortController = new AbortController();
    chatAbortRef.current = abortController;

    const humanMessage = { role: "human", content: question };
    const placeholderAi = {
      role: "ai",
      content: "",
      streaming: true,
      completion: null,
    };
    const historyForApi = [...chatMessages, humanMessage];

    setChatMessages([...historyForApi, placeholderAi]);
    setChatInput("");
    setChatError("");
    setChatLoading(true);

    const updateStreamingMessage = (updater) => {
      setChatMessages((prev) => {
        if (prev.length === 0) {
          return prev;
        }
        const next = [...prev];
        const lastIndex = next.length - 1;
        const last = next[lastIndex];
        if (last?.role !== "ai") {
          return prev;
        }
        next[lastIndex] = updater(last);
        return next;
      });
    };

    try {
      await sendChatMessage(
        question,
        historyForApi,
        selectedVectorStoreId.trim() || undefined,
        {
          signal: abortController.signal,
          onEvent: (evt) =>
            handleChatStreamEvent(evt, {
              updateStreamingMessage,
              setChatError,
              emptyAnswerText: "No response from assistant.",
              streamFailedText: "Chat stream failed.",
            }),
        },
      );
    } catch (err) {
      if (err?.name !== "AbortError") {
        setChatError("Failed to send chat request.");
        updateStreamingMessage((msg) => ({
          ...msg,
          streaming: false,
          content: msg.content || "Failed to get a response.",
        }));
      }
    } finally {
      if (chatAbortRef.current === abortController) {
        chatAbortRef.current = null;
      }
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
      <div
        className={`dashboard-wrapper${activeView === "knowledge-bases" ? " dashboard-wrapper--kb" : ""}`}
      >
        <DashboardHeader
          isLightTheme={isLightTheme}
          onToggleTheme={() => setIsLightTheme((value) => !value)}
          activeView={activeView}
          onNavigate={navigate}
        />

        {activeView === "dashboard" ? (
          <>
            <main className="dashboard-grid">
              <SimulationPanel
                mapView={mapView}
                onRunScenario={handleRunScenario}
                onTriggerEvent={handleTriggerEvent}
                simulationLoading={simulationLoading}
                simulationError={simulationError}
                vectorStores={vectorStores}
                setSelectedVectorStoreId={setSelectedVectorStoreId}
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
              vectorStores={vectorStores}
              vectorStoresLoading={vectorStoresLoading}
              vectorStoresError={vectorStoresError}
              selectedVectorStoreId={selectedVectorStoreId}
              onChangeVectorStore={setSelectedVectorStoreId}
            />
          </>
        ) : (
          <KnowledgeBasesPage onKnowledgeBaseCreated={reloadVectorStores} />
        )}
      </div>
    </div>
  );
}

export default App;
