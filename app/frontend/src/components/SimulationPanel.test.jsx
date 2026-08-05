import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SimulationPanel } from "./SimulationPanel";

describe("SimulationPanel", () => {
  it("renders heading and all preset buttons", () => {
    render(<SimulationPanel />);
    expect(screen.getByRole("heading", { name: /AI Simulation/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Live Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Port Strike/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Suez Blockage/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Trigger World Event/i })).toBeInTheDocument();
  });

  it("calls onRunScenario with correct scenario when preset clicked", async () => {
    const onRunScenario = vi.fn();
    render(<SimulationPanel onRunScenario={onRunScenario} setSelectedVectorStoreId={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /Port Strike/i }));
    expect(onRunScenario).toHaveBeenCalledWith({ scenario: "port-strike", optimize: false });
  });

  it("disables buttons while simulation is loading", () => {
    render(<SimulationPanel simulationLoading />);
    const buttons = screen.getAllByRole("button");
    buttons.forEach((btn) => expect(btn).toBeDisabled());
  });

  it("shows loading text while simulation is running", () => {
    render(<SimulationPanel simulationLoading />);
    expect(screen.getByText(/Running simulation/i)).toBeInTheDocument();
  });

  it("shows error text when simulationError is set", () => {
    render(<SimulationPanel simulationError="Something broke" />);
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("calls onTriggerEvent with mapView when Trigger World Event clicked", async () => {
    const onTriggerEvent = vi.fn();
    render(<SimulationPanel mapView="global" onTriggerEvent={onTriggerEvent} setSelectedVectorStoreId={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /Trigger World Event/i }));
    expect(onTriggerEvent).toHaveBeenCalledWith("global");
  });

  it("finds matching vector store and calls setSelectedVectorStoreId", async () => {
    const onRunScenario = vi.fn();
    const setSelectedVectorStoreId = vi.fn();
    render(
      <SimulationPanel
        onRunScenario={onRunScenario}
        setSelectedVectorStoreId={setSelectedVectorStoreId}
        vectorStores={[
          { id: "vs-1", name: "port-risk-data" },
        ]}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: /Port Strike/i }));
    expect(setSelectedVectorStoreId).toHaveBeenCalledWith("vs-1");
  });
});
