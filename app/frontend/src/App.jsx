import { useCallback, useEffect, useRef, useState } from "react";
import { applyChatStreamEvent } from "./utils/chatStream.js";
import { ChatBar } from "./components/ChatBar";
import { CreateScenarioPage } from "./components/CreateScenarioPage";
import { DashboardHeader } from "./components/DashboardHeader";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { KnowledgeBasesPage } from "./components/KnowledgeBasesPage";
import { ImpactSimulationPage } from "./components/ImpactSimulationPage";
import { NewsTicker } from "./components/NewsTicker";
import { findVectorStoreIdForScenario } from "./services/presetScenarioIds";
import { getVectorStores, sendChatMessageStream } from "./services/dashboardService";
import { getNews } from "./services/newsService";

const NEWS_POLL_MS = 5 * 60 * 1000;

function hashPathAndQuery() {
  const raw = window.location.hash.replace(/^#/, "");
  const [pathPart, queryPart = ""] = raw.split("?");
  const path = pathPart.replace(/^\//, "");
  return { path, query: new URLSearchParams(queryPart) };
}

function viewFromHash() {
  const { path } = hashPathAndQuery();
  if (path === "knowledge-bases") {
    return "knowledge-bases";
  }
  if (path === "create-scenario") {
    return "create-scenario";
  }
  return "simulation";
}

function scenarioIdFromHash() {
  return hashPathAndQuery().query.get("scenario") || "";
}

function chatKeyForScenario(scenarioId) {
  return scenarioId || "_default";
}

function App() {
  const [isLightTheme, setIsLightTheme] = useState(false);
  const [chatMessagesByScenario, setChatMessagesByScenario] = useState({});
  const [chatInputByScenario, setChatInputByScenario] = useState({});
  const [chatErrorByScenario, setChatErrorByScenario] = useState({});
  const [chatLoadingByScenario, setChatLoadingByScenario] = useState({});
  const [vectorStores, setVectorStores] = useState([]);
  const [vectorStoresError, setVectorStoresError] = useState("");
  const [activeView, setActiveView] = useState(viewFromHash);
  const [activeScenarioId, setActiveScenarioId] = useState(scenarioIdFromHash);
  const [chatSimulation, setChatSimulation] = useState(null);
  const [newsItems, setNewsItems] = useState([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const chatAbortRef = useRef(null);
  const newsAbortRef = useRef(null);
  const chatLoadingRef = useRef(false);

  const chatKey = chatKeyForScenario(activeScenarioId);
  const chatMessages = chatMessagesByScenario[chatKey] || [];
  const chatInput = chatInputByScenario[chatKey] || "";
  const chatError = chatErrorByScenario[chatKey] || "";
  const chatLoading = Boolean(chatLoadingByScenario[chatKey]);
  chatLoadingRef.current = chatLoading;
  const matchedVectorStoreId = findVectorStoreIdForScenario(vectorStores, activeScenarioId);
  const chatRagHint = (() => {
    if (vectorStoresError) {
      return vectorStoresError;
    }
    if (!activeScenarioId || vectorStores.length === 0) {
      return "";
    }
    if (!matchedVectorStoreId) {
      return "No knowledge base matched this scenario; chat will run without document retrieval.";
    }
    return "";
  })();

  const reloadVectorStores = useCallback(async (signal) => {
    try {
      const res = await getVectorStores({ signal });
      if (signal?.aborted) return;
      setVectorStores(Array.isArray(res.vector_stores) ? res.vector_stores : []);
      setVectorStoresError("");
    } catch (err) {
      if (err?.name === "AbortError") return;
      setVectorStores([]);
      setVectorStoresError("Unable to load knowledge bases for chat retrieval.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    reloadVectorStores(controller.signal);
    return () => controller.abort();
  }, [reloadVectorStores]);

  useEffect(() => {
    const onHashChange = () => {
      setActiveView(viewFromHash());
      const fromHash = scenarioIdFromHash();
      if (fromHash) {
        setActiveScenarioId(fromHash);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const { path } = hashPathAndQuery();
    if (path === "" || path === "dashboard") {
      const scenario = scenarioIdFromHash();
      const qs = scenario ? `?scenario=${encodeURIComponent(scenario)}` : "";
      window.location.hash = `#/simulation${qs}`;
    }
  }, []);

  useEffect(() => {
    return () => {
      chatAbortRef.current?.abort();
    };
  }, []);

  const loadNews = useCallback(async () => {
    // Skip RSS refresh while chat is using the shared CPU/network budget.
    if (chatLoadingRef.current) return;
    newsAbortRef.current?.abort();
    const controller = new AbortController();
    newsAbortRef.current = controller;
    try {
      const res = await getNews({ signal: controller.signal });
      if (controller.signal.aborted) return;
      setNewsItems(Array.isArray(res?.items) ? res.items : []);
    } catch (err) {
      if (err?.name === "AbortError") return;
      // Keep prior headlines on refresh failure; empty only on first load.
      setNewsItems((prev) => (Array.isArray(prev) ? prev : []));
    } finally {
      if (newsAbortRef.current === controller) {
        newsAbortRef.current = null;
        setNewsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    loadNews();
    const timer = window.setInterval(loadNews, NEWS_POLL_MS);
    return () => {
      window.clearInterval(timer);
      newsAbortRef.current?.abort();
    };
  }, [loadNews]);

  const navigate = (view, { scenarioId } = {}) => {
    if (view === "knowledge-bases") {
      window.location.hash = "#/knowledge-bases";
      return;
    }
    if (view === "create-scenario") {
      window.location.hash = "#/create-scenario";
      return;
    }
    const qs = scenarioId ? `?scenario=${encodeURIComponent(scenarioId)}` : "";
    window.location.hash = `#/simulation${qs}`;
  };

  const handleScenarioCreated = useCallback((scenarioId) => {
    const nextId = scenarioId || "";
    setActiveScenarioId(nextId);
    const qs = nextId ? `?scenario=${encodeURIComponent(nextId)}` : "";
    window.location.hash = `#/simulation${qs}`;
  }, []);

  const handleActiveScenarioChange = useCallback((scenarioId) => {
    const nextId = scenarioId || "";
    setActiveScenarioId((prev) => {
      if (prev !== nextId) {
        chatAbortRef.current?.abort();
        chatAbortRef.current = null;
      }
      return nextId;
    });
    if (nextId) {
      const current = scenarioIdFromHash();
      if (current !== nextId) {
        window.location.hash = `#/simulation?scenario=${encodeURIComponent(nextId)}`;
      }
    }
  }, []);

  const handleChangeChatInput = useCallback(
    (value) => {
      setChatInputByScenario((prev) => ({ ...prev, [chatKey]: value }));
    },
    [chatKey],
  );

  const handleSubmitChat = async () => {
    const question = chatInput.trim();
    if (!question || chatLoading) {
      return;
    }

    const scenarioKey = chatKey;
    const vectorStoreId = matchedVectorStoreId;
    const humanMessage = { role: "human", content: question };
    const historyForApi = [...(chatMessagesByScenario[scenarioKey] || []), humanMessage];
    const aiPlaceholder = { role: "ai", content: "", completion: null };

    chatAbortRef.current?.abort();
    const controller = new AbortController();
    chatAbortRef.current = controller;

    setChatMessagesByScenario((prev) => ({
      ...prev,
      [scenarioKey]: [...historyForApi, aiPlaceholder],
    }));
    setChatInputByScenario((prev) => ({ ...prev, [scenarioKey]: "" }));
    setChatErrorByScenario((prev) => ({ ...prev, [scenarioKey]: "" }));
    setChatLoadingByScenario((prev) => ({ ...prev, [scenarioKey]: true }));
    try {
      await sendChatMessageStream(
        question,
        historyForApi,
        vectorStoreId.trim() || undefined,
        true,
        (event) => {
          if (controller.signal.aborted) return;
          if (event?.type === "done" && event.simulation) {
            setChatSimulation({
              ...event.simulation,
              answer: event.answer || event.simulation.answer,
              success: true,
            });
          }
          setChatMessagesByScenario((prev) => {
            const current = prev[scenarioKey] || [];
            const next = applyChatStreamEvent(current, event);
            return next ? { ...prev, [scenarioKey]: next } : prev;
          });
        },
        { signal: controller.signal, scenarioId: activeScenarioId },
      );
    } catch (err) {
      if (err?.name === "AbortError") return;
      setChatErrorByScenario((prev) => ({
        ...prev,
        [scenarioKey]:
          err instanceof Error && err.message
            ? err.message
            : "Failed to send chat request.",
      }));
      setChatMessagesByScenario((prev) => ({ ...prev, [scenarioKey]: historyForApi }));
    } finally {
      if (chatAbortRef.current === controller) {
        chatAbortRef.current = null;
      }
      setChatLoadingByScenario((prev) => ({ ...prev, [scenarioKey]: false }));
    }
  };

  return (
    <div className={`dashboard-root ${isLightTheme ? "light-theme" : ""}`}>
      <ErrorBoundary>
        <div
          className={`dashboard-wrapper${
            activeView === "knowledge-bases" || activeView === "create-scenario"
              ? " dashboard-wrapper--kb"
              : " dashboard-wrapper--simulation"
          }`}
        >
          <DashboardHeader
            isLightTheme={isLightTheme}
            onToggleTheme={() => setIsLightTheme((value) => !value)}
            activeView={activeView}
            onNavigate={navigate}
          />

          {activeView === "knowledge-bases" ? (
            <KnowledgeBasesPage onKnowledgeBaseCreated={reloadVectorStores} />
          ) : activeView === "create-scenario" ? (
            <CreateScenarioPage onCreated={handleScenarioCreated} />
          ) : (
            <>
              <NewsTicker items={newsItems} loading={newsLoading} />
              <ImpactSimulationPage
                initialScenarioId={activeScenarioId}
                onScenarioChange={handleActiveScenarioChange}
                chatSimulation={chatSimulation}
                chatLoading={chatLoading}
              />
              <ChatBar
                chatInput={chatInput}
                onChangeChatInput={handleChangeChatInput}
                onSubmitChat={handleSubmitChat}
                chatLoading={chatLoading}
                chatError={chatError}
                chatMessages={chatMessages}
                chatRagHint={chatRagHint}
              />
            </>
          )}
        </div>
      </ErrorBoundary>
    </div>
  );
}

export default App;
