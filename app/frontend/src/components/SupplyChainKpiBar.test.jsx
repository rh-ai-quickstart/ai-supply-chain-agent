import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SupplyChainKpiBar } from "./SupplyChainKpiBar";

const SAMPLE_KPIS = {
  inStock: { value: "83%", trend: "▼ 3%", trendDirection: "down", trendSentiment: "bad" },
  onTime: { value: "76%", trend: "▼ 5%", trendDirection: "down", trendSentiment: "bad" },
  turnover: { value: "5.2x", trend: "▼ 0.4x", trendDirection: "down", trendSentiment: "bad" },
  lostSales: { value: "$2.1M", trend: "▲ $2.1M", trendDirection: "up", trendSentiment: "bad" },
  reorderPoint: { value: "39%", trend: "▲ 11%", trendDirection: "up", trendSentiment: "caution" },
};

describe("SupplyChainKpiBar", () => {
  it("renders all five KPI labels", () => {
    render(<SupplyChainKpiBar />);

    expect(screen.getByText("In-Stock Rate")).toBeInTheDocument();
    expect(screen.getByText("On-Time Delivery")).toBeInTheDocument();
    expect(screen.getByText("Inventory Turnover")).toBeInTheDocument();
    expect(screen.getByText("Lost Sales")).toBeInTheDocument();
    expect(screen.getByText("Optimal Reorder")).toBeInTheDocument();
  });

  it("shows placeholders while loading", () => {
    render(<SupplyChainKpiBar loading />);
    expect(screen.getAllByText("—")).toHaveLength(5);
  });

  it("renders API KPI values and trends", () => {
    render(<SupplyChainKpiBar kpis={SAMPLE_KPIS} />);

    expect(screen.getByText("83%")).toBeInTheDocument();
    expect(screen.getByText("76%")).toBeInTheDocument();
    expect(screen.getByText("5.2x")).toBeInTheDocument();
    expect(screen.getByText("$2.1M")).toBeInTheDocument();
    expect(screen.getByText("39%")).toBeInTheDocument();
    expect(screen.getByText("▲ $2.1M")).toBeInTheDocument();
  });

  it("shows an error message when provided", () => {
    render(<SupplyChainKpiBar error="Unable to load KPIs." />);
    expect(screen.getByRole("status")).toHaveTextContent("Unable to load KPIs.");
  });
});
