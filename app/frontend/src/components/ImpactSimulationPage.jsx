import { useCallback, useEffect, useMemo, useState } from "react";
import { ImpactMapPanel } from "./ImpactMapPanel";
import { DEFAULT_IMPACT_QUESTION, ImpactQueryPanel } from "./ImpactQueryPanel";
import { ImpactResultsPanel } from "./ImpactResultsPanel";
import {
  getImpactEntitiesGeoJson,
  listImpactScenarios,
  runImpactQuery,
} from "../services/generalSimulationService";

export const EUROPE_BBOX = "-15,35,40,62";
export const DEFAULT_GEOJSON_LIMIT = 3000;

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

export function ImpactSimulationPage() {
  const [scenarios, setScenarios] = useState([]);
  const [scenariosLoading, setScenariosLoading] = useState(true);
  const [scenariosError, setScenariosError] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [question, setQuestion] = useState(DEFAULT_IMPACT_QUESTION);

  const [collection, setCollection] = useState({ type: "FeatureCollection", features: [] });
  const [mapLoading, setMapLoading] = useState(true);
  const [mapError, setMapError] = useState("");

  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setScenariosLoading(true);
      setMapLoading(true);
      setScenariosError("");
      setMapError("");
      try {
        const [scenarioRes, geoRes] = await Promise.all([
          listImpactScenarios({ signal: controller.signal }),
          getImpactEntitiesGeoJson({
            bbox: EUROPE_BBOX,
            limit: DEFAULT_GEOJSON_LIMIT,
            signal: controller.signal,
          }),
        ]);
        if (controller.signal.aborted) return;

        if (scenarioRes.success === false) {
          setScenariosError(scenarioRes.error || "Unable to load scenarios.");
          setScenarios([]);
        } else {
          const list = Array.isArray(scenarioRes.scenarios) ? scenarioRes.scenarios : [];
          setScenarios(list);
          if (list.length > 0) setScenarioId(list[0]);
        }

        if (geoRes.success === false) {
          setMapError(geoRes.error || "Unable to load map entities.");
        } else {
          setCollection(geoRes.geojson || { type: "FeatureCollection", features: [] });
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        setScenariosError("Unable to load scenarios.");
        setMapError("Unable to load map entities.");
      } finally {
        if (!controller.signal.aborted) {
          setScenariosLoading(false);
          setMapLoading(false);
        }
      }
    })();
    return () => controller.abort();
  }, []);

  const handleRunQuery = useCallback(async () => {
    setQueryError("");
    setQueryLoading(true);
    try {
      const res = await runImpactQuery({ question, scenarioId });
      if (res.success === false) {
        setQueryError(res.error || "Impact query failed.");
        return;
      }
      setResult(res);

      const affected = Array.isArray(res.affected_entities) ? res.affected_entities : [];
      if (affected.length > 0) {
        try {
          const overlay = await getImpactEntitiesGeoJson({
            ids: affected,
            limit: affected.length,
          });
          if (overlay.success !== false && overlay.geojson) {
            setCollection((prev) => mergeFeatureCollections(prev, overlay.geojson));
          }
        } catch {
          /* keep existing map; highlights still apply when features are present */
        }
      }
    } catch {
      setQueryError("Impact query failed.");
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

  return (
    <main className="dashboard-grid impact-simulation-grid">
      <ImpactQueryPanel
        scenarios={scenarios}
        scenariosLoading={scenariosLoading}
        scenariosError={scenariosError}
        scenarioId={scenarioId}
        onChangeScenarioId={setScenarioId}
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
          loading={mapLoading}
          error={mapError}
        />
      </section>

      <ImpactResultsPanel result={result} loading={queryLoading} />
    </main>
  );
}
