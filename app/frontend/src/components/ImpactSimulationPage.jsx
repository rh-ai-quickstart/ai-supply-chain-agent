import { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { ImpactMapPanel } from "./ImpactMapPanel";
import { DEFAULT_IMPACT_QUESTION, ImpactQueryPanel } from "./ImpactQueryPanel";
import { ImpactResultsPanel } from "./ImpactResultsPanel";
import {
  getImpactEntitiesGeoJson,
  listImpactScenarios,
  runImpactQuery,
} from "../services/generalSimulationService";
import {
  bboxForScenario,
  questionForScenario,
} from "../services/presetScenarioIds";
import {
  buildValueByEntity,
  diversionKey,
} from "../utils/impactEntityUtils";

export const DEFAULT_GEOJSON_LIMIT = 3000;

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

function messageFromError(err, fallback) {
  if (err?.name === "AbortError") return "";
  const msg = err instanceof Error ? err.message.trim() : "";
  return msg || fallback;
}

export function ImpactSimulationPage({ initialScenarioId = "", onScenarioChange }) {
  const [scenarios, setScenarios] = useState([]);
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [scenariosError, setScenariosError] = useState("");
  const [scenarioId, setScenarioId] = useState(initialScenarioId);
  const [question, setQuestion] = useState(DEFAULT_IMPACT_QUESTION);

  const [collection, setCollection] = useState({ type: "FeatureCollection", features: [] });
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState("");
  const [mapWarning, setMapWarning] = useState("");

  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [result, setResult] = useState(null);
  const [focusedEntityId, setFocusedEntityId] = useState("");
  const [focusNonce, setFocusNonce] = useState(0);
  const [selectedDiversionKey, setSelectedDiversionKey] = useState("");
  const [diversionFocusNonce, setDiversionFocusNonce] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setScenariosLoading(true);
      setScenariosError("");
      try {
        const scenarioRes = await listImpactScenarios({ signal: controller.signal });
        if (controller.signal.aborted) return;

        if (scenarioRes.success === false) {
          setScenariosError(scenarioRes.error || "Unable to load scenarios.");
          setScenarios([]);
        } else {
          const list = Array.isArray(scenarioRes.scenarios) ? scenarioRes.scenarios : [];
          setScenarios(list);
          const selected = pickScenarioId(list, initialScenarioId);
          setScenarioId(selected);
          if (selected) {
            setQuestion(questionForScenario(selected));
          }
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
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
      setMapLoading(false);
      return;
    }
    const controller = new AbortController();
    (async () => {
      setMapLoading(true);
      setMapError("");
      setMapWarning("");
      try {
        const geoRes = await getImpactEntitiesGeoJson({
          bbox: bboxForScenario(scenarioId),
          limit: DEFAULT_GEOJSON_LIMIT,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (geoRes.success === false) {
          setMapError(geoRes.error || "Unable to load map entities.");
          return;
        }
        setCollection(geoRes.geojson || { type: "FeatureCollection", features: [] });
        setResult(null);
        setFocusedEntityId("");
        setSelectedDiversionKey("");
        setDiversionFocusNonce(0);
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
  }, [scenarioId]);

  const handleChangeScenarioId = useCallback((nextId) => {
    setScenarioId(nextId);
    setQuestion(questionForScenario(nextId));
    setQueryError("");
  }, []);

  useEffect(() => {
    if (!scenarioId) return;
    onScenarioChange?.(scenarioId);
  }, [scenarioId, onScenarioChange]);

  const handleRunQuery = useCallback(async () => {
    setQueryError("");
    setMapWarning("");
    setQueryLoading(true);
    try {
      const res = await runImpactQuery({ question, scenarioId });
      if (res.success === false) {
        setQueryError(res.error || "Impact query failed.");
        return;
      }
      setResult(res);
      setFocusedEntityId("");
      setFocusNonce(0);
      setSelectedDiversionKey("");
      setDiversionFocusNonce(0);

      const affected = Array.isArray(res.affected_entities) ? res.affected_entities : [];
      if (affected.length > 0) {
        try {
          const overlay = await getImpactEntitiesGeoJson({
            ids: affected,
            limit: affected.length,
          });
          if (overlay.success === false) {
            setMapWarning(overlay.error || "Some affected entities could not be loaded onto the map.");
          } else if (overlay.geojson) {
            setCollection((prev) => mergeFeatureCollections(prev, overlay.geojson));
          }
        } catch (err) {
          setMapWarning(messageFromError(err, "Some affected entities could not be loaded onto the map."));
        }
      }
    } catch (err) {
      setQueryError(messageFromError(err, "Impact query failed."));
    } finally {
      setQueryLoading(false);
    }
  }, [question, scenarioId]);

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

  return (
    <main className="dashboard-grid impact-simulation-grid">
      <ImpactQueryPanel
        scenarios={scenarios}
        scenariosLoading={scenariosLoading}
        scenariosError={scenariosError}
        scenarioId={scenarioId}
        onChangeScenarioId={handleChangeScenarioId}
        question={question}
        onChangeQuestion={setQuestion}
        onRunQuery={handleRunQuery}
        queryLoading={queryLoading}
        queryError={queryError}
      />

      <section className="center-content">
        <ImpactMapPanel
          features={collection.features}
          highlightedIds={highlightedIds}
          reroutes={reroutes}
          focusedEntityId={focusedEntityId}
          focusNonce={focusNonce}
          selectedDiversionKey={selectedDiversionKey}
          diversionFocusNonce={diversionFocusNonce}
          valueByEntity={valueByEntity}
          currency={currency}
          loading={mapLoading}
          error={mapError}
          warning={mapWarning}
        />
      </section>

      <ImpactResultsPanel
        result={result}
        loading={queryLoading}
        onFocusEntity={handleFocusEntity}
        onFocusDiversion={handleFocusDiversion}
        focusedDiversionKey={selectedDiversionKey}
      />
    </main>
  );
}

ImpactSimulationPage.propTypes = {
  initialScenarioId: PropTypes.string,
  onScenarioChange: PropTypes.func,
};
