import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DemandChartPanel } from "./DemandChartPanel";

describe("DemandChartPanel", () => {
  it("renders chart title and mocked chart region", () => {
    render(
      <DemandChartPanel
        data={{
          labels: ["Jan"],
          datasets: [{ label: "Actual", data: [1] }, { label: "Forecast", data: [2] }],
        }}
      />
    );
    expect(screen.getByRole("heading", { name: /demand forecast/i })).toBeInTheDocument();
    expect(screen.getByTestId("mock-line-chart")).toBeInTheDocument();
  });
});
