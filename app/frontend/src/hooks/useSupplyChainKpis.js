import { useEffect, useMemo, useState } from "react";
import { getSupplyChainKpis, postSupplyChainKpis } from "../services/kpiService";
import { GLOBAL_DEMO_BBOX } from "../services/presetScenarioIds";
import { messageFromError } from "../utils/errorMessage";

function impactSnapshotKey(impactResult) {
  if (!impactResult?.solver) return "";
  const affected = Array.isArray(impactResult.affected_entities)
    ? impactResult.affected_entities.join(",")
    : "";
  const score = impactResult.solver.impact_score ?? "";
  const var_ = impactResult.solver.total_value_at_risk ?? "";
  return `${impactResult.scenario_id || ""}:${score}:${var_}:${affected}`;
}

export function useSupplyChainKpis({
  scenarioId = "",
  impactResult = null,
  chatLoading = false,
}) {
  const [kpis, setKpis] = useState(null);
  const [dataQuality, setDataQuality] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const impactKey = useMemo(() => impactSnapshotKey(impactResult), [impactResult]);

  useEffect(() => {
    if (chatLoading) {
      return undefined;
    }

    const controller = new AbortController();
    (async () => {
      setLoading(true);
      setError("");
      try {
        const response = await getSupplyChainKpis({
          scenarioId,
          bbox: GLOBAL_DEMO_BBOX,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response?.success === false) {
          setError(response.error || "Unable to load KPIs.");
          setKpis(null);
          setDataQuality(null);
          return;
        }
        setKpis(response.kpis || null);
        setDataQuality(response.data_quality || null);
      } catch (err) {
        if (err?.name === "AbortError") return;
        setError(messageFromError(err, "Unable to load KPIs."));
        setKpis(null);
        setDataQuality(null);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    })();

    return () => controller.abort();
  }, [scenarioId, chatLoading]);

  useEffect(() => {
    if (chatLoading || !impactKey || !impactResult?.solver) {
      return undefined;
    }

    const controller = new AbortController();
    (async () => {
      setRefreshing(true);
      setError("");
      try {
        const response = await postSupplyChainKpis({
          scenarioId: impactResult.scenario_id || scenarioId,
          bbox: GLOBAL_DEMO_BBOX,
          solver: impactResult.solver,
          affectedEntities: impactResult.affected_entities,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response?.success === false) {
          setError(response.error || "Unable to refresh KPIs.");
          return;
        }
        setKpis(response.kpis || null);
        setDataQuality(response.data_quality || null);
      } catch (err) {
        if (err?.name === "AbortError") return;
        setError(messageFromError(err, "Unable to refresh KPIs."));
      } finally {
        if (!controller.signal.aborted) {
          setRefreshing(false);
        }
      }
    })();

    return () => controller.abort();
  }, [impactKey, impactResult, scenarioId, chatLoading]);

  return {
    kpis,
    dataQuality,
    loading: loading || refreshing,
    error,
  };
}
