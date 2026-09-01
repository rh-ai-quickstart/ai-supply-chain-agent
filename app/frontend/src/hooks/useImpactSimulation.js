import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getImpactEntitiesGeoJson,
  listImpactScenarios,
  runImpactQuery,
} from "../services/generalSimulationService";
import {
  DEFAULT_IMPACT_QUESTION,
  GLOBAL_DEMO_BBOX,
  bboxForScenario,
  questionForScenario,
} from "../services/presetScenarioIds";
import { buildValueByEntity, diversionKey } from "../utils/impactEntityUtils";
import { messageFromError } from "../utils/errorMessage";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);
const DEFAULT_GEOJSON_LIMIT = 3000;

function pickScenarioId(list, preferred) {
  if (!Array.isArray(list) || list.length === 0) return "";
  if (preferred && list.includes(preferred)) return preferred;
  return list[0];
}

function mergeFeatureCollections(base, overlay) {
  const byId = new Map();
  for (const feature of base?.features ?? []) {
    const id = feature.properties?.id ?? feature.id;
    if (id != null) byId.set(id, feature);
  }
  for (const feature of overlay?.features ?? []) {
    const id = feature.properties?.id ?? feature.id;
    if (id != null) byId.set(id, feature);
  }
  return {
    type: "FeatureCollection",
    features: [...byId.values()],
  };
}

/**
 * Impact-simulation orchestration, extracted from `ImpactSimulationPage.jsx`
 * (SRP): scenario loading, map GeoJSON loading, impact query execution, and
 * map focus/diversion selection state. The component is left composing
 * `ImpactQueryPanel` / `ImpactMapPanel` / `ImpactResultsPanel` from this
 * hook's return value.
 */
export function useImpactSimulation({
  initialScenarioId = "",
  onScenarioChange,
  chatSimulation = null,
  chatLoading = false,
}) {
  const [scenarios, setScenarios] = useState([]);
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [scenariosError, setScenariosError] = useState("");
  const [scenarioId, setScenarioId] = useState(initialScenarioId);
  const [question, setQuestion] = useState(DEFAULT_IMPACT_QUESTION);

  const [collection, setCollection] = useState({ type: "FeatureCollection", features: [] });
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState("");
  const [mapWarning, setMapWarning] = useState("");
  const [mapScenarioId, setMapScenarioId] = useState("");

  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [result, setResult] = useState(null);
  const [resultScenarioId, setResultScenarioId] = useState("");
  const [focusedEntityId, setFocusedEntityId] = useState("");
  const [focusNonce, setFocusNonce] = useState(0);
  const [selectedDiversionKey, setSelectedDiversionKey] = useState("");
  const [diversionFocusNonce, setDiversionFocusNonce] = useState(0);
  /** ``live`` = world fit (default); ``scenario`` = camera framed to scenario bbox. */
  const [mapMode, setMapMode] = useState("live");

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      logger.debug("useImpactSimulation: loading scenarios, initial=%s", initialScenarioId);
      setScenariosLoading(true);
      setScenariosError("");
      try {
        const scenarioRes = await listImpactScenarios({ signal: controller.signal });
        if (controller.signal.aborted) return;

        if (scenarioRes.success === false) {
          setScenariosError(scenarioRes.error || "Unable to load scenarios.");
          setScenarios([]);
          logger.error("useImpactSimulation scenarios error: %s", scenarioRes.error);
        } else {
          const list = Array.isArray(scenarioRes.scenarios) ? scenarioRes.scenarios : [];
          setScenarios(list);
          const selected = pickScenarioId(list, initialScenarioId);
          setScenarioId(selected);
          if (selected) {
            setQuestion(questionForScenario(selected));
          }
          logger.debug("useImpactSimulation: loaded %d scenarios", list.length);
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        logger.error("useImpactSimulation scenarios error: %s", err.message);
        setScenariosError(messageFromError(err, "Unable to load scenarios."));
        setScenarios([]);
      } finally {
        if (!controller.signal.aborted) {
          setScenariosLoading(false);
        }
      }
    })();
    return () => controller.abort();
  }, [initialScenarioId]);

  useEffect(() => {
    if (!initialScenarioId || scenarios.length === 0) return;
    if (scenarios.includes(initialScenarioId)) {
      setScenarioId(initialScenarioId);
      setQuestion(questionForScenario(initialScenarioId));
    }
  }, [initialScenarioId, scenarios]);

  useEffect(() => {
    if (!scenarioId) {
      setCollection({ type: "FeatureCollection", features: [] });
      setMapScenarioId("");
      setMapLoading(false);
      return;
    }
    // Defer heavy map loads while chat is using the LLM / gen-sim stack.
    if (chatLoading) {
      return;
    }
    if (mapScenarioId === scenarioId) {
      return;
    }
    const controller = new AbortController();
    (async () => {
      setMapLoading(true);
      setMapError("");
      setMapWarning("");
      try {
        // Load the full seeded demo world; scenario bbox is camera-only (focusBbox).
        const geoRes = await getImpactEntitiesGeoJson({
          bbox: GLOBAL_DEMO_BBOX,
          limit: DEFAULT_GEOJSON_LIMIT,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (geoRes.success === false) {
          setMapError(geoRes.error || "Unable to load map entities.");
          return;
        }
        setCollection(geoRes.geojson || { type: "FeatureCollection", features: [] });
        setMapScenarioId(scenarioId);
      } catch (err) {
        if (err?.name === "AbortError") return;
        setMapError(messageFromError(err, "Unable to load map entities."));
      } finally {
        if (!controller.signal.aborted) {
          setMapLoading(false);
        }
      }
    })();
    return () => controller.abort();
  }, [scenarioId, chatLoading, mapScenarioId]);

  const applySimulationResult = useCallback(
    async (res, scenario) => {
      if (!res || res.success === false) return;
      setResult(res);
      setResultScenarioId(scenario || "");
      setQueryError("");
      setFocusedEntityId("");
      setFocusNonce(0);
      setSelectedDiversionKey("");
      setDiversionFocusNonce(0);
      if (res.question) {
        setQuestion(res.question);
      }

      const affected = Array.isArray(res.affected_entities) ? res.affected_entities : [];
      if (affected.length === 0) return;

      try {
        const overlay = await getImpactEntitiesGeoJson({
          ids: affected,
          limit: affected.length,
        });
        if (overlay.success === false) {
          setMapWarning(overlay.error || "Some affected entities could not be loaded onto the map.");
        } else if (overlay.geojson) {
          setCollection((prev) => mergeFeatureCollections(prev, overlay.geojson));
          setMapWarning("");
        }
      } catch (err) {
        setMapWarning(messageFromError(err, "Some affected entities could not be loaded onto the map."));
      }
    },
    [],
  );

  const runQuery = useCallback(
    async (scenario, prompt) => {
      if (chatLoading) return;
      if (!scenario || !prompt) return;
      logger.info("useImpactSimulation: runQuery: scenario=%s question=%s", scenario, prompt.slice(0, 80));
      setQueryError("");
      setMapWarning("");
      setQueryLoading(true);
      try {
        const res = await runImpactQuery({ question: prompt, scenarioId: scenario });
        if (res.success === false) {
          logger.error("useImpactSimulation runQuery error: %s", res.error);
          setQueryError(res.error || "Impact query failed.");
          return;
        }
        logger.info("useImpactSimulation: runQuery success: scenario=%s", scenario);
        await applySimulationResult(res, scenario);
      } catch (err) {
        logger.error("useImpactSimulation runQuery error: %s", err.message);
        setQueryError(messageFromError(err, "Impact query failed."));
      } finally {
        setQueryLoading(false);
      }
    },
    [applySimulationResult, chatLoading],
  );

  const handleRunQuery = useCallback(() => {
    return runQuery(scenarioId, question);
  }, [runQuery, scenarioId, question]);

  const handleRunSuggestedPrompt = useCallback(
    (prompt) => {
      setQuestion(prompt);
      return runQuery(scenarioId, prompt);
    },
    [runQuery, scenarioId],
  );

  const handleChangeScenarioId = useCallback(
    (nextId) => {
      const nextQuestion = questionForScenario(nextId);
      if (nextId !== scenarioId) {
        setMapScenarioId("");
        setResult(null);
        setResultScenarioId("");
        setFocusedEntityId("");
        setSelectedDiversionKey("");
        setDiversionFocusNonce(0);
        onScenarioChange?.(nextId);
      }
      setScenarioId(nextId);
      setQuestion(nextQuestion);
      setQueryError("");
      setMapMode("scenario");
      void runQuery(nextId, nextQuestion);
    },
    [onScenarioChange, runQuery, scenarioId],
  );

  const handleMapModeChange = useCallback((mode) => {
    if (mode === "live" || mode === "scenario") {
      setMapMode(mode);
    }
  }, []);

  useEffect(() => {
    if (!scenarioId) return;
    onScenarioChange?.(scenarioId);
  }, [scenarioId, onScenarioChange]);

  useEffect(() => {
    if (!chatSimulation) return;
    void applySimulationResult(chatSimulation, scenarioId);
  }, [chatSimulation, scenarioId, applySimulationResult]);

  const highlightedIds = useMemo(
    () => (Array.isArray(result?.affected_entities) ? result.affected_entities : []),
    [result],
  );
  const reroutes = useMemo(
    () =>
      Array.isArray(result?.solver?.recommended_reroutes)
        ? result.solver.recommended_reroutes
        : [],
    [result],
  );
  const valueByEntity = useMemo(
    () => buildValueByEntity(result?.solver?.value_breakdown),
    [result],
  );
  const currency = result?.solver?.currency || "USD";

  const handleFocusEntity = useCallback((entityId) => {
    setFocusedEntityId(entityId);
    setFocusNonce((value) => value + 1);
    setSelectedDiversionKey("");
  }, []);

  const handleFocusDiversion = useCallback((route) => {
    const key = diversionKey(route);
    setSelectedDiversionKey(key);
    setDiversionFocusNonce((value) => value + 1);
    if (route?.entity_id) {
      setFocusedEntityId(route.entity_id);
      setFocusNonce((value) => value + 1);
    }
  }, []);

  const focusBbox = useMemo(() => {
    if (mapMode !== "scenario" || !scenarioId) return "";
    return bboxForScenario(scenarioId);
  }, [mapMode, scenarioId]);

  const mapTitle = mapMode === "live" ? "Live Flights" : "Impact Map";

  return {
    scenarios,
    scenariosLoading,
    scenariosError,
    scenarioId,
    question,
    setQuestion,
    handleChangeScenarioId,

    mapMode,
    handleMapModeChange,
    mapTitle,

    collection,
    mapLoading,
    mapError,
    mapWarning,
    focusBbox,

    queryLoading,
    queryError,
    result,
    handleRunQuery,
    handleRunSuggestedPrompt,

    highlightedIds,
    reroutes,
    valueByEntity,
    currency,

    focusedEntityId,
    focusNonce,
    selectedDiversionKey,
    diversionFocusNonce,
    handleFocusEntity,
    handleFocusDiversion,
  };
}
