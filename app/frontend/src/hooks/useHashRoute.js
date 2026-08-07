import { useCallback, useEffect, useState } from "react";

/**
 * Hand-rolled hash-based routing, extracted from `App.jsx` (SRP): parses
 * `#/<path>?<query>` into a view + scenario id, keeps them in sync with
 * `hashchange`, and exposes `navigate`/`setActiveScenarioId` for callers
 * that need to change the URL or React state explicitly.
 */

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

export function useHashRoute() {
  const [activeView, setActiveView] = useState(viewFromHash);
  const [activeScenarioId, setActiveScenarioIdState] = useState(scenarioIdFromHash);

  useEffect(() => {
    const onHashChange = () => {
      setActiveView(viewFromHash());
      const fromHash = scenarioIdFromHash();
      if (fromHash) {
        setActiveScenarioIdState(fromHash);
      }
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const { path } = hashPathAndQuery();
    if (path === "" || path === "dashboard" || path === "live") {
      const scenario = scenarioIdFromHash();
      const qs = scenario ? `?scenario=${encodeURIComponent(scenario)}` : "";
      window.location.hash = `#/simulation${qs}`;
    }
  }, []);

  const navigate = useCallback((view, { scenarioId } = {}) => {
    if (view === "knowledge-bases") {
      window.location.hash = "#/knowledge-bases";
      return;
    }
    if (view === "create-scenario") {
      window.location.hash = "#/create-scenario";
      return;
    }
    // Legacy ``live`` tab is folded into Simulation (map mode toggle).
    const qs = scenarioId ? `?scenario=${encodeURIComponent(scenarioId)}` : "";
    window.location.hash = `#/simulation${qs}`;
  }, []);

  const setActiveScenarioId = useCallback((nextId) => {
    setActiveScenarioIdState(nextId);
  }, []);

  /** Update the URL's `scenario` query param without changing the current path/view. */
  const syncScenarioHash = useCallback((nextId) => {
    if (!nextId) return;
    const current = scenarioIdFromHash();
    if (current !== nextId) {
      window.location.hash = `#/simulation?scenario=${encodeURIComponent(nextId)}`;
    }
  }, []);

  return { activeView, activeScenarioId, setActiveScenarioId, syncScenarioHash, navigate };
}
