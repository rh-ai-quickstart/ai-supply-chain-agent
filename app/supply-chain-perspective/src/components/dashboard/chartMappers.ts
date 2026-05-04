import type { ChartData } from 'chart.js';
import type {
  DashboardAlert,
  DashboardState,
  MapLayerData,
  MapViewId,
  SystemHealthRiskLevel,
  SystemHealthView,
} from '../../types/dashboard';

function parsePercent(value: string | undefined, fallback = 0): number {
  if (!value) {
    return fallback;
  }
  const parsed = parseInt(String(value).replace('%', ''), 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export function getKpis(dashboardState: DashboardState | null): Record<string, { value?: string }> {
  return dashboardState?.kpis ?? {};
}

export function getFlattenedAlerts(dashboardState: DashboardState | null): DashboardAlert[] {
  const allAlerts = dashboardState?.alerts ?? {};
  return [
    ...(allAlerts.global ?? []),
    ...(allAlerts.regional ?? []),
    ...(allAlerts.airFreight ?? []),
  ];
}

export function getAssetCounts(dashboardState: DashboardState | null): {
  air: number;
  sea: number;
  land: number;
} {
  return {
    air: dashboardState?.mapData?.airFreight?.assets?.length ?? 0,
    sea: dashboardState?.mapData?.global?.assets?.length ?? 0,
    land: dashboardState?.mapData?.regional?.assets?.length ?? 0,
  };
}

export function getSelectedMapData(
  dashboardState: DashboardState | null,
  mapView: MapViewId,
): MapLayerData {
  return dashboardState?.mapData?.[mapView] ?? { ports: [] };
}

/** Chart.js reads literal colors on canvas (CSS variables are unreliable here). */
export function toDemandChartData(dashboardState: DashboardState | null): ChartData<'line'> {
  const demand = dashboardState?.charts?.demand;
  return {
    labels: demand?.labels ?? [],
    datasets: [
      {
        label: 'Actual',
        data: demand?.actual ?? [],
        borderColor: '#06c',
        backgroundColor: 'rgba(0, 102, 204, 0.15)',
      },
      {
        label: 'Forecast',
        data: demand?.forecast ?? [],
        borderColor: '#5c35a0',
        backgroundColor: 'rgba(92, 53, 160, 0.15)',
      },
    ],
  };
}

export function toRevenueChartData(dashboardState: DashboardState | null): ChartData<'bar'> {
  const revenue = dashboardState?.charts?.revenue;
  const labels = ['Electronics', 'Apparel', 'Essentials', 'Home', 'Perishables'];
  return {
    labels,
    datasets: [
      {
        label: 'Revenue %',
        data: revenue?.revenueData ?? [],
        backgroundColor: (revenue?.colors ?? []).map((color) =>
          color === 'green' ? '#3e8635' : '#c9190b',
        ),
      },
    ],
  };
}

export function toSystemHealthMetrics(
  kpis: Record<string, { value?: string }>,
  alerts: DashboardAlert[],
  loading: boolean,
  error: string,
): SystemHealthView {
  const onTimePercent = parsePercent(kpis.onTime?.value, 85);
  const inStockPercent = parsePercent(kpis.inStock?.value, 92);
  const criticalAlertCount = alerts.filter((alert) => alert.type === 'critical').length;
  const riskIndex = Math.min(100, Math.max(0, 100 - onTimePercent + criticalAlertCount * 12));
  const riskLevel: SystemHealthRiskLevel =
    riskIndex > 60 ? 'critical' : riskIndex > 35 ? 'medium' : 'low';
  const dataFreshnessPercent = error ? 0 : loading ? 65 : 100;

  return {
    supplierHealth: onTimePercent,
    inventoryHealth: inStockPercent,
    riskIndex,
    riskLevel,
    dataFreshnessPercent,
  };
}
