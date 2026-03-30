function parsePercent(value, fallback = 0) {
  if (!value) {
    return fallback;
  }
  const parsed = parseInt(String(value).replace("%", ""), 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export function getKpis(dashboardState) {
  return dashboardState?.kpis ?? {};
}

export function getFlattenedAlerts(dashboardState) {
  const allAlerts = dashboardState?.alerts ?? {};
  return [
    ...(allAlerts.global ?? []),
    ...(allAlerts.regional ?? []),
    ...(allAlerts.airFreight ?? []),
  ];
}

export function getAssetCounts(dashboardState) {
  return {
    air: dashboardState?.mapData?.airFreight?.assets?.length ?? 0,
    sea: dashboardState?.mapData?.global?.assets?.length ?? 0,
    land: dashboardState?.mapData?.regional?.assets?.length ?? 0,
  };
}

export function getSelectedMapData(dashboardState, mapView) {
  return dashboardState?.mapData?.[mapView] ?? { ports: [] };
}

export function toDemandChartData(dashboardState) {
  const demand = dashboardState?.charts?.demand;
  return {
    labels: demand?.labels ?? [],
    datasets: [
      {
        label: "Actual",
        data: demand?.actual ?? [],
        borderColor: "#FF4757",
        backgroundColor: "rgba(255, 71, 87, 0.3)",
      },
      {
        label: "Forecast",
        data: demand?.forecast ?? [],
        borderColor: "#00E0FF",
        backgroundColor: "rgba(0, 224, 255, 0.3)",
      },
    ],
  };
}

export function toRevenueChartData(dashboardState) {
  const revenue = dashboardState?.charts?.revenue;
  const labels = ["Electronics", "Apparel", "Essentials", "Home", "Perishables"];
  return {
    labels,
    datasets: [
      {
        label: "Revenue %",
        data: revenue?.revenueData ?? [],
        backgroundColor: (revenue?.colors ?? []).map((color) =>
          color === "green" ? "#2ECC71" : "#FF4757"
        ),
      },
    ],
  };
}

export function toSystemHealthMetrics(kpis, alerts, loading, error) {
  const onTimePercent = parsePercent(kpis.onTime?.value, 85);
  const inStockPercent = parsePercent(kpis.inStock?.value, 92);
  const criticalAlertCount = alerts.filter((alert) => alert.type === "critical").length;
  const riskIndex = Math.min(100, Math.max(0, 100 - onTimePercent + criticalAlertCount * 12));
  const riskLabel = riskIndex > 60 ? "Critical" : riskIndex > 35 ? "Medium" : "Low";
  const dataFreshnessPercent = error ? 0 : loading ? 65 : 100;

  return {
    supplierHealth: onTimePercent,
    inventoryHealth: inStockPercent,
    riskIndex,
    riskLabel,
    dataFreshnessPercent,
  };
}
