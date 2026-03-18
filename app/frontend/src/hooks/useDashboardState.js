import { useEffect, useState } from "react";
import { getDashboardState } from "../services/dashboardService";

const REFRESH_INTERVAL_MS = 15000;

export function useDashboardState() {
  const [dashboardState, setDashboardState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refreshState = async () => {
    try {
      setError("");
      const data = await getDashboardState();
      setDashboardState(data);
      return data;
    } catch {
      setError("Unable to load dashboard state from backend.");
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const loadState = async () => {
      try {
        setError("");
        const data = await getDashboardState();
        if (!cancelled) {
          setDashboardState(data);
        }
      } catch {
        if (!cancelled) {
          setError("Unable to load dashboard state from backend.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadState();
    const timerId = setInterval(loadState, REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(timerId);
    };
  }, []);

  return { dashboardState, loading, error, refreshState, setDashboardState };
}
