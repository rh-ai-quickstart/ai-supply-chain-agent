import { useCallback, useEffect, useMemo, useState } from 'react';
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

    const nextHistory: ChatMessage[] = [...chatMessages, { role: 'human', content: question }];
    setChatMessages(nextHistory);
    setChatInput('');
    setChatError('');
    setChatLoading(true);
    try {
      const result = await postAssistantMessage(
        question,
        nextHistory,
        selectedVectorStoreId.trim() || undefined,
      );
      const answer: string = result?.answer ?? t('No response from assistant.');
      const completion = result?.completion ?? null;
      setChatMessages((current) => [
        ...current,
        { role: 'ai' as const, content: answer, completion },
      ]);
    } catch {
      setChatError(t('Failed to send chat request.'));
    } finally {
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
