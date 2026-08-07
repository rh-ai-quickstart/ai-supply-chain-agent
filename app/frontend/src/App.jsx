import { useCallback, useState } from "react";
import { ChatBar } from "./components/ChatBar";
import { CreateScenarioPage } from "./components/CreateScenarioPage";
import { DashboardHeader } from "./components/DashboardHeader";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { KnowledgeBasesPage } from "./components/KnowledgeBasesPage";
import { ImpactSimulationPage } from "./components/ImpactSimulationPage";
import { NewsTicker } from "./components/NewsTicker";
import { useChatSession } from "./hooks/useChatSession";
import { useHashRoute } from "./hooks/useHashRoute";
import { useNewsFeed } from "./hooks/useNewsFeed";
import { useVectorStores } from "./hooks/useVectorStores";

function App() {
  const [isLightTheme, setIsLightTheme] = useState(false);
  const { activeView, activeScenarioId, setActiveScenarioId, syncScenarioHash, navigate } =
    useHashRoute();
  const { vectorStores, vectorStoresError, reloadVectorStores } = useVectorStores();
  const chat = useChatSession({ vectorStores, vectorStoresError, activeScenarioId });
  const { newsItems, newsLoading } = useNewsFeed(chat.chatLoading);

  const handleScenarioCreated = useCallback(
    (scenarioId) => {
      const nextId = scenarioId || "";
      setActiveScenarioId(nextId);
      navigate("simulation", { scenarioId: nextId });
    },
    [navigate, setActiveScenarioId],
  );

  const handleActiveScenarioChange = useCallback(
    (scenarioId) => {
      const nextId = scenarioId || "";
      if (nextId !== activeScenarioId) {
        chat.abortActiveStream();
      }
      setActiveScenarioId(nextId);
      syncScenarioHash(nextId);
    },
    [activeScenarioId, chat, setActiveScenarioId, syncScenarioHash],
  );

  const isKbOrCreate =
    activeView === "knowledge-bases" || activeView === "create-scenario";

  return (
    <div className={`dashboard-root ${isLightTheme ? "light-theme" : ""}`}>
      <ErrorBoundary>
        <div
          className={`dashboard-wrapper${
            isKbOrCreate ? " dashboard-wrapper--kb" : " dashboard-wrapper--simulation"
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
                chatSimulation={chat.chatSimulation}
                chatLoading={chat.chatLoading}
              />
              <ChatBar
                chatInput={chat.chatInput}
                onChangeChatInput={chat.handleChangeChatInput}
                onSubmitChat={chat.handleSubmitChat}
                chatLoading={chat.chatLoading}
                chatError={chat.chatError}
                chatMessages={chat.chatMessages}
                chatRagHint={chat.chatRagHint}
              />
            </>
          )}
        </div>
      </ErrorBoundary>
    </div>
  );
}

export default App;
