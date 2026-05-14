import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SystemHealthPanel } from "./SystemHealthPanel";

describe("SystemHealthPanel", () => {
  it("renders labels and values from health metrics", () => {
    const health = {
      supplierHealth: 92,
      inventoryHealth: 96,
      riskIndex: 20,
      riskLabel: "Low",
      dataFreshnessPercent: 100,
    };
    render(<SystemHealthPanel health={health} />);
    expect(screen.getByRole("heading", { name: /system health/i })).toBeInTheDocument();
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("Low")).toBeInTheDocument();
  });
});
