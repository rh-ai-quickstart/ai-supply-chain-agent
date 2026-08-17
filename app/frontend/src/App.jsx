import { useCallback, useState } from "react";
import { ChatBar } from "./components/ChatBar";
import { CreateScenarioModal } from "./components/CreateScenarioModal";
import { DashboardHeader } from "./components/DashboardHeader";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { KnowledgeBasesPage } from "./components/KnowledgeBasesPage";
import { ImpactSimulationPage } from "./components/ImpactSimulationPage";
import { useChatSession } from "./hooks/useChatSession";
import { useHashRoute } from "./hooks/useHashRoute";
import { useNewsFeed } from "./hooks/useNewsFeed";
import { useVectorStores } from "./hooks/useVectorStores";
import { formatNewsItemForScenarioPrompt } from "./utils/newsScenarioPrompt";

function App() {
  const [isLightTheme, setIsLightTheme] = useState(false);
  const [isCreateScenarioOpen, setIsCreateScenarioOpen] = useState(false);
  const [createScenarioInitialPrompt, setCreateScenarioInitialPrompt] = useState("");
  const { activeView, activeScenarioId, setActiveScenarioId, syncScenarioHash, navigate } =
    useHashRoute();
  const { vectorStores, vectorStoresError, reloadVectorStores } = useVectorStores();
  const {
    abortActiveStream,
    chatInput,
    chatError,
    chatLoading,
    chatMessages,
    chatRagHint,
    chatSimulation,
    clearChat,
    handleChangeChatInput,
    handleSubmitChat,
    knowledgeBaseName,
    sendPrompt,
  } = useChatSession({ vectorStores, vectorStoresError, activeScenarioId });
  const { newsItems, newsLoading } = useNewsFeed(chatLoading);

  const handleOpenCreateScenario = useCallback((prompt = "") => {
    setCreateScenarioInitialPrompt(typeof prompt === "string" ? prompt : "");
    setIsCreateScenarioOpen(true);
  }, []);

  const handleCloseCreateScenario = useCallback(() => {
    setIsCreateScenarioOpen(false);
    setCreateScenarioInitialPrompt("");
  }, []);

  const handleScenarioCreated = useCallback(
    (scenarioId) => {
      const nextId = scenarioId || "";
      handleCloseCreateScenario();
      setActiveScenarioId(nextId);
      navigate("simulation", { scenarioId: nextId });
    },
    [handleCloseCreateScenario, navigate, setActiveScenarioId],
  );

  const handleCreateScenarioFromNews = useCallback(
    (item) => {
      const prompt = formatNewsItemForScenarioPrompt(item);
      if (prompt) {
        handleOpenCreateScenario(prompt);
      }
    },
    [handleOpenCreateScenario],
  );

  const handleActiveScenarioChange = useCallback(
    (scenarioId) => {
      const nextId = scenarioId || "";
      if (nextId !== activeScenarioId) {
        abortActiveStream();
      }
      setActiveScenarioId(nextId);
      syncScenarioHash(nextId);
    },
    [abortActiveStream, activeScenarioId, setActiveScenarioId, syncScenarioHash],
  );

  const isKnowledgeBases = activeView === "knowledge-bases";

  return (
    <div className={`dashboard-root ${isLightTheme ? "light-theme" : ""}`}>
      <ErrorBoundary>
        <div
          className={`dashboard-wrapper${
            isKnowledgeBases ? " dashboard-wrapper--kb" : " dashboard-wrapper--simulation"
          }`}
        >
          <DashboardHeader
            isLightTheme={isLightTheme}
            onToggleTheme={() => setIsLightTheme((value) => !value)}
            activeView={activeView}
            onNavigate={navigate}
            newsItems={newsItems}
            newsLoading={newsLoading}
            onCreateScenarioFromNews={handleCreateScenarioFromNews}
          />

          {isKnowledgeBases ? (
            <KnowledgeBasesPage onKnowledgeBaseCreated={reloadVectorStores} />
          ) : (
            <>
              <ImpactSimulationPage
                initialScenarioId={activeScenarioId}
                onScenarioChange={handleActiveScenarioChange}
                onOpenCreateScenario={handleOpenCreateScenario}
                chatSimulation={chatSimulation}
                chatLoading={chatLoading}
                onSendPrompt={sendPrompt}
              />
              <ChatBar
                chatInput={chatInput}
                onChangeChatInput={handleChangeChatInput}
                onSubmitChat={handleSubmitChat}
                chatLoading={chatLoading}
                chatError={chatError}
                chatMessages={chatMessages}
                chatRagHint={chatRagHint}
                knowledgeBaseName={knowledgeBaseName}
                onClearChat={clearChat}
              />
              {isCreateScenarioOpen ? (
                <CreateScenarioModal
                  initialPrompt={createScenarioInitialPrompt}
                  onClose={handleCloseCreateScenario}
                  onCreated={handleScenarioCreated}
                />
              ) : null}
            </>
          )}
        </div>
      </ErrorBoundary>
    </div>
  );
}

export default App;
