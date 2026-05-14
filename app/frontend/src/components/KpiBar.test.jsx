import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { KpiBar } from "./KpiBar";

describe("KpiBar", () => {
  it("renders KPI values from props", () => {
    render(
      <KpiBar
        kpis={{
          inStock: { value: "95%" },
          onTime: { value: "91%" },
          turnover: { value: "4.2x" },
          lostSales: { value: "$1.2M" },
          reorderPoint: { value: "78%" },
        }}
      />
    );
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.getByText("4.2x")).toBeInTheDocument();
  });

  it("shows placeholders when values are missing", () => {
    render(<KpiBar kpis={{}} />);
    expect(screen.getAllByText("--%").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("--x")).toBeInTheDocument();
  });
});
