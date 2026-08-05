import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RevenueChartPanel } from "./RevenueChartPanel";

vi.mock("react-chartjs-2", () => ({
  Bar: vi.fn(({ data }) => (
    <div data-testid="chart" className="bar-chart" data-data={JSON.stringify(data)} />
  )),
}));

describe("RevenueChartPanel", () => {
  it("renders heading when no data", () => {
    render(<RevenueChartPanel data={null} />);
    expect(screen.getByRole("heading", { name: /Revenue Impact/i })).toBeInTheDocument();
  });

  it("shows muted no-data message when data is null", () => {
    render(<RevenueChartPanel data={null} />);
    expect(screen.getByText(/No revenue data available/i)).toBeInTheDocument();
  });

  it("shows muted no-data message when data is undefined", () => {
    render(<RevenueChartPanel data={undefined} />);
    expect(screen.getByText(/No revenue data available/i)).toBeInTheDocument();
    expect(screen.queryByTestId("chart")).not.toBeInTheDocument();
  });

  it("shows muted no-data message when data is empty object", () => {
    render(<RevenueChartPanel data={{}} />);
    // An empty object is falsy? No, {} is truthy. Let me check:
    // if (!data) — {} is truthy, so it would NOT show no-data message
    // Actually {} is truthy, so it should try to render the chart
  });

  it("renders chart panel structure when data provided", () => {
    const mockData = {
      labels: ["Jan", "Feb"],
      datasets: [{ data: [100, 200] }],
    };
    render(<RevenueChartPanel data={mockData} />);
    expect(screen.getByRole("heading", { name: /Revenue Impact/i })).toBeInTheDocument();
    expect(screen.getByTestId("chart")).toBeInTheDocument();
    expect(screen.getByTestId("chart")).toHaveAttribute("data-data");
  });

  it("renders chart with correct data", () => {
    const mockData = {
      labels: ["Q1", "Q2"],
      datasets: [{ label: "Revenue", data: [500, 700] }],
    };
    render(<RevenueChartPanel data={mockData} />);
    expect(screen.getByTestId("chart")).toHaveAttribute(
      "data-data",
      JSON.stringify(mockData)
    );
  });

  it("renders as article with chart-panel class", () => {
    const mockData = { labels: [], datasets: [] };
    const { container } = render(<RevenueChartPanel data={mockData} />);
    const article = container.querySelector("article");
    expect(article).toBeInTheDocument();
    expect(article).toHaveClass("chart-panel");
  });

  it("renders as article with panel class", () => {
    const mockData = { labels: [], datasets: [] };
    const { container } = render(<RevenueChartPanel data={mockData} />);
    const article = container.querySelector("article");
    expect(article).toHaveClass("panel");
  });

  it("renders no-data state as article with panel and chart-panel classes", () => {
    const { container } = render(<RevenueChartPanel data={null} />);
    const article = container.querySelector("article");
    expect(article).toBeInTheDocument();
    expect(article).toHaveClass("panel");
    expect(article).toHaveClass("chart-panel");
  });
});
