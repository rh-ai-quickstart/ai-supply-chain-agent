import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type {
  ChatMessage,
  DashboardState,
  MapViewId,
  VectorStoreSummary,
} from '../../types/dashboard';
import {
  fetchDashboardState,
  fetchVectorStores,
  postAssistantMessage,
  postSimulation,
  postTriggerWorldEvent,
} from './backendClient';
import {
  getAssetCounts,
  getFlattenedAlerts,
  getKpis,
  getSelectedMapData,
  toDemandChartData,
  toRevenueChartData,
  toSystemHealthMetrics,
} from './chartMappers';
import { handleChatStreamEvent } from '../../utils/handleChatStreamEvent';

const REFRESH_INTERVAL_MS = 15000;

export function useDashboardController() {
  const { t } = useTranslation('plugin__supply-chain-perspective');
  const [isLightTheme, setIsLightTheme] = useState(false);
  const [mapView, setMapView] = useState<MapViewId>('airFreight');
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationError, setSimulationError] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState('');
  const [vectorStores, setVectorStores] = useState<VectorStoreSummary[]>([]);
  const [vectorStoresLoading, setVectorStoresLoading] = useState(false);
  const [vectorStoresError, setVectorStoresError] = useState('');
  const [selectedVectorStoreId, setSelectedVectorStoreId] = useState('');
  const [dashboardState, setDashboardState] = useState<DashboardState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const chatAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        setError('');
        const data = await fetchDashboardState();
        if (!cancelled) {
          setDashboardState(data);
        }
      } catch {
        if (!cancelled) {
          setError(t('Unable to load dashboard state from backend.'));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void poll();
    const timerId = window.setInterval(() => {
      void poll();
    }, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timerId);
    };
  }, [t]);

  useEffect(() => {
    let cancelled = false;
    const loadStores = async () => {
      setVectorStoresLoading(true);
      setVectorStoresError('');
      try {
        const res = await fetchVectorStores();
        if (!cancelled) {
          setVectorStores(Array.isArray(res.vector_stores) ? res.vector_stores : []);
          if (res.error) {
            setVectorStoresError(res.error);
          }
        }
      } catch {
        if (!cancelled) {
          setVectorStoresError(t('Unable to load vector stores from LlamaStack.'));
          setVectorStores([]);
        }
      } finally {
        if (!cancelled) {
          setVectorStoresLoading(false);
        }
      }
    };
    void loadStores();
    return () => {
      cancelled = true;
    };
  }, [t]);

  const handleRunScenario = useCallback(
    async ({ scenario, optimize }: { scenario: string; optimize: boolean }) => {
      setSimulationError('');
      setSimulationLoading(true);
      try {
        const result = await postSimulation(scenario, optimize);
        setDashboardState(result);
      } catch {
        setSimulationError(t('Failed to run simulation.'));
      } finally {
        setSimulationLoading(false);
      }
    },
    [t],
  );

  const handleTriggerEvent = useCallback(
    async (selectedMapView: MapViewId) => {
      setSimulationError('');
      setSimulationLoading(true);
      try {
        const result = await postTriggerWorldEvent(selectedMapView);
        setDashboardState(result);
      } catch {
        setSimulationError(t('Failed to trigger event.'));
      } finally {
        setSimulationLoading(false);
      }
    },
    [t],
  );

  const handleSubmitChat = useCallback(async () => {
    const question = chatInput.trim();
    if (!question || chatLoading) {
      return;
    }

    chatAbortRef.current?.abort();
    const abortController = new AbortController();
    chatAbortRef.current = abortController;

    const humanMessage: ChatMessage = { role: 'human', content: question };
    const placeholderAi: ChatMessage = {
      role: 'ai',
      content: '',
      streaming: true,
      completion: null,
    };
    const historyForApi: ChatMessage[] = [...chatMessages, humanMessage];

    setChatMessages([...historyForApi, placeholderAi]);
    setChatInput('');
    setChatError('');
    setChatLoading(true);

    const updateStreamingMessage = (updater: (_msg: ChatMessage) => ChatMessage) => {
      setChatMessages((prev) => {
        if (prev.length === 0) {
          return prev;
        }
        const next = [...prev];
        const lastIndex = next.length - 1;
        const last = next[lastIndex];
        if (last?.role !== 'ai') {
          return prev;
        }
        next[lastIndex] = updater(last);
        return next;
      });
    };

    try {
      await postAssistantMessage(
        question,
        historyForApi,
        selectedVectorStoreId.trim() || undefined,
        {
          signal: abortController.signal,
          onEvent: (evt) =>
            handleChatStreamEvent(evt, {
              updateStreamingMessage,
              setChatError,
              emptyAnswerText: t('No response from assistant.'),
              streamFailedText: t('Chat stream failed.'),
            }),
        },
      );
    } catch (err) {
      if ((err as Error)?.name !== 'AbortError') {
        setChatError(t('Failed to send chat request.'));
        updateStreamingMessage((msg) => ({
          ...msg,
          streaming: false,
          content: msg.content || t('Failed to get a response.'),
        }));
      }
    } finally {
      if (chatAbortRef.current === abortController) {
        chatAbortRef.current = null;
      }
      setChatLoading(false);
    }
  }, [chatInput, chatLoading, chatMessages, selectedVectorStoreId, t]);

  const kpis = useMemo(() => getKpis(dashboardState), [dashboardState]);
  const alerts = useMemo(() => getFlattenedAlerts(dashboardState), [dashboardState]);
  const assetCounts = useMemo(() => getAssetCounts(dashboardState), [dashboardState]);
  const selectedMapData = useMemo(
    () => getSelectedMapData(dashboardState, mapView),
    [dashboardState, mapView],
  );
  const demandData = useMemo(() => toDemandChartData(dashboardState), [dashboardState]);
  const revenueData = useMemo(() => toRevenueChartData(dashboardState), [dashboardState]);
  const systemHealth = useMemo(
    () => toSystemHealthMetrics(kpis, alerts, loading, error),
    [kpis, alerts, loading, error],
  );

  return {
    isLightTheme,
    setIsLightTheme,
    mapView,
    setMapView,
    simulationLoading,
    simulationError,
    chatInput,
    setChatInput,
    chatMessages,
    chatLoading,
    chatError,
    vectorStores,
    vectorStoresLoading,
    vectorStoresError,
    selectedVectorStoreId,
    setSelectedVectorStoreId,
    dashboardState,
    loading,
    error,
    handleRunScenario,
    handleTriggerEvent,
    handleSubmitChat,
    kpis,
    alerts,
    assetCounts,
    selectedMapData,
    demandData,
    revenueData,
    systemHealth,
  };
}
