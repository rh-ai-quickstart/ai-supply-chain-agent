import { describe, expect, it } from 'vitest';
import type { DashboardState } from '../../types/dashboard';
import {
  getAssetCounts,
  getFlattenedAlerts,
  getKpis,
  getSelectedMapData,
  toDemandChartData,
  toRevenueChartData,
  toSystemHealthMetrics,
} from './chartMappers';

describe('getKpis', () => {
  it('returns empty object when state is null', () => {
    expect(getKpis(null)).toEqual({});
  });

  it('returns kpis from state', () => {
    const state = { kpis: { onTime: { value: '90%' } } } as DashboardState;
    expect(getKpis(state)).toEqual({ onTime: { value: '90%' } });
  });
});

describe('getFlattenedAlerts', () => {
  it('concatenates alert buckets', () => {
    const state = {
      alerts: {
        global: [{ type: 'info', text: 'g' }],
        regional: [{ type: 'warn', text: 'r' }],
        airFreight: [{ type: 'critical', text: 'a' }],
      },
    } as DashboardState;
    expect(getFlattenedAlerts(state)).toHaveLength(3);
  });
});

describe('getAssetCounts', () => {
  it('counts assets per layer', () => {
    const state = {
      mapData: {
        airFreight: { assets: [{}, {}] },
        global: { assets: [{}] },
        regional: { assets: [] },
      },
    } as DashboardState;
    expect(getAssetCounts(state)).toEqual({ air: 2, sea: 1, land: 0 });
  });
});

describe('getSelectedMapData', () => {
  it('returns default ports when missing', () => {
    expect(getSelectedMapData(null, 'airFreight')).toEqual({ ports: [] });
  });
});

describe('toDemandChartData', () => {
  it('maps demand series', () => {
    const state = {
      charts: { demand: { labels: ['Q1'], actual: [1], forecast: [2] } },
    } as DashboardState;
    const chart = toDemandChartData(state);
    expect(chart.labels).toEqual(['Q1']);
    expect(chart.datasets[0].data).toEqual([1]);
    expect(chart.datasets[1].data).toEqual([2]);
  });
});

describe('toRevenueChartData', () => {
  it('maps PatternFly-aligned bar colors', () => {
    const state = {
      charts: { revenue: { revenueData: [1, 2], colors: ['green', 'red'] } },
    } as DashboardState;
    const chart = toRevenueChartData(state);
    expect(chart.datasets[0].backgroundColor).toEqual(['#3e8635', '#c9190b']);
  });
});

describe('toSystemHealthMetrics', () => {
  it('computes risk level and freshness', () => {
    const m = toSystemHealthMetrics(
      { onTime: { value: '88%' }, inStock: { value: '96%' } },
      [],
      false,
      '',
    );
    expect(m.supplierHealth).toBe(88);
    expect(m.riskLevel).toBe('low');
    expect(m.dataFreshnessPercent).toBe(100);
  });

  it('escalates to critical when alerts and low on-time combine', () => {
    const m = toSystemHealthMetrics(
      { onTime: { value: '40%' }, inStock: { value: '90%' } },
      [
        { type: 'critical', text: 'a' },
        { type: 'critical', text: 'b' },
      ],
      false,
      '',
    );
    expect(m.riskLevel).toBe('critical');
  });

  it('sets freshness to 0 on error', () => {
    const m = toSystemHealthMetrics({}, [], false, 'err');
    expect(m.dataFreshnessPercent).toBe(0);
  });
});
