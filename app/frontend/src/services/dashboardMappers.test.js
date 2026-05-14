import { describe, expect, it } from "vitest";
import {
  getAssetCounts,
  getFlattenedAlerts,
  getKpis,
  getSelectedMapData,
  toDemandChartData,
  toRevenueChartData,
  toSystemHealthMetrics,
} from "./dashboardMappers";

describe("getKpis", () => {
  it("returns empty object when state is missing", () => {
    expect(getKpis(null)).toEqual({});
    expect(getKpis(undefined)).toEqual({});
  });

  it("returns kpis from state", () => {
    expect(getKpis({ kpis: { onTime: { value: "90%" } } })).toEqual({ onTime: { value: "90%" } });
  });
});

describe("getFlattenedAlerts", () => {
  it("concatenates global, regional, and airFreight alerts in order", () => {
    const state = {
      alerts: {
        global: [{ type: "info", text: "g" }],
        regional: [{ type: "warn", text: "r" }],
        airFreight: [{ type: "critical", text: "a" }],
      },
    };
    expect(getFlattenedAlerts(state)).toEqual([
      { type: "info", text: "g" },
      { type: "warn", text: "r" },
      { type: "critical", text: "a" },
    ]);
  });

  it("treats missing buckets as empty", () => {
    expect(getFlattenedAlerts({ alerts: {} })).toEqual([]);
  });
});

describe("getAssetCounts", () => {
  it("counts assets per map layer", () => {
    const state = {
      mapData: {
        airFreight: { assets: [1, 2] },
        global: { assets: [1] },
        regional: { assets: [] },
      },
    };
    expect(getAssetCounts(state)).toEqual({ air: 2, sea: 1, land: 0 });
  });
});

describe("getSelectedMapData", () => {
  it("returns slice for known map view", () => {
    const state = { mapData: { airFreight: { ports: [{ name: "P" }], assets: [] } } };
    expect(getSelectedMapData(state, "airFreight")).toEqual({ ports: [{ name: "P" }], assets: [] });
  });

  it("returns default when view or state missing", () => {
    expect(getSelectedMapData(null, "airFreight")).toEqual({ ports: [] });
    expect(getSelectedMapData({ mapData: {} }, "unknown")).toEqual({ ports: [] });
  });
});

describe("toDemandChartData", () => {
  it("fills labels and series from demand chart state", () => {
    const state = {
      charts: {
        demand: { labels: ["Q1"], actual: [1], forecast: [2] },
      },
    };
    const chart = toDemandChartData(state);
    expect(chart.labels).toEqual(["Q1"]);
    expect(chart.datasets[0].data).toEqual([1]);
    expect(chart.datasets[1].data).toEqual([2]);
  });
});

describe("toRevenueChartData", () => {
  it("maps green vs non-green colors onto revenue bars", () => {
    const state = {
      charts: {
        revenue: {
          revenueData: [10, 20],
          colors: ["green", "red"],
        },
      },
    };
    const chart = toRevenueChartData(state);
    expect(chart.datasets[0].backgroundColor).toEqual(["#2ECC71", "#FF4757"]);
  });
});

describe("toSystemHealthMetrics", () => {
  it("uses KPI strings for health and labels risk bands", () => {
    const kpis = {
      onTime: { value: "88%" },
      inStock: { value: "96%" },
    };
    const alerts = [];
    const m = toSystemHealthMetrics(kpis, alerts, false, "");
    expect(m.supplierHealth).toBe(88);
    expect(m.inventoryHealth).toBe(96);
    expect(m.riskLabel).toBe("Low");
  });

  it("escalates risk label when critical alerts stack", () => {
    const kpis = { onTime: { value: "50%" }, inStock: { value: "90%" } };
    const alerts = [
      { type: "critical", text: "a" },
      { type: "critical", text: "b" },
    ];
    const m = toSystemHealthMetrics(kpis, alerts, false, "");
    expect(m.riskIndex).toBeGreaterThan(60);
    expect(m.riskLabel).toBe("Critical");
  });

  it("sets data freshness to 0 when there is an error", () => {
    const m = toSystemHealthMetrics({}, [], false, "boom");
    expect(m.dataFreshnessPercent).toBe(0);
  });

  it("sets data freshness to 65 while loading", () => {
    const m = toSystemHealthMetrics({}, [], true, "");
    expect(m.dataFreshnessPercent).toBe(65);
  });
});
