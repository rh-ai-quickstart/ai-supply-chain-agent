import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ImpactQueryPanel } from "./ImpactQueryPanel";

describe("ImpactQueryPanel", () => {
  it("renders scenario buttons and suggested prompts without a question field or run button", () => {
    render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        mapMode="live"
        onChangeMapMode={vi.fn()}
        onChangeScenarioId={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: /Scenario Selection/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create scenario/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: "All Flights" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: /About suggested prompts/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/Question/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Run Scenario/i })).not.toBeInTheDocument();
  });

  it("calls onChangeMapMode when All Flights is clicked", async () => {
    const onChangeMapMode = vi.fn();
    render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        mapMode="scenario"
        onChangeMapMode={onChangeMapMode}
        onChangeScenarioId={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "All Flights" }));
    expect(onChangeMapMode).toHaveBeenCalledWith("live");
  });

  it("calls onChangeScenarioId when a scenario button is clicked", async () => {
    const onChangeScenarioId = vi.fn();
    render(
      <ImpactQueryPanel
        scenarios={["supply-chain-port-strike-la", "opensky-uk-closure-001"]}
        scenarioId="supply-chain-port-strike-la"
        onChangeScenarioId={onChangeScenarioId}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "UK Airspace Closure" }));
    expect(onChangeScenarioId).toHaveBeenCalledWith("opensky-uk-closure-001");
  });

  it("shows loading and error states", () => {
    render(
      <ImpactQueryPanel
        scenarios={["s1"]}
        scenarioId="s1"
        queryLoading
        queryError="Upstream failed"
        onChangeScenarioId={vi.fn()}
      />,
    );
    expect(screen.getByText(/Running Scenario/i)).toBeInTheDocument();
    expect(screen.getByText("Upstream failed")).toBeInTheDocument();
  });

  it("renders suggested prompts for the selected scenario and runs one on click", async () => {
    const onRunSuggestedPrompt = vi.fn();
    render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        onChangeScenarioId={vi.fn()}
        onRunSuggestedPrompt={onRunSuggestedPrompt}
      />,
    );
    expect(screen.getByRole("button", { name: /About suggested prompts/i })).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /Show affected aircraft/i }),
    );
    expect(onRunSuggestedPrompt).toHaveBeenCalledWith(
      "Show affected aircraft and recommend diversions.",
    );
  });

  it("calls onCreateScenario when Create scenario is clicked", async () => {
    const onCreateScenario = vi.fn();
    render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        onChangeScenarioId={vi.fn()}
        onCreateScenario={onCreateScenario}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Create scenario/i }));
    expect(onCreateScenario).toHaveBeenCalledTimes(1);
  });

  it("keeps scenario controls in a scroll region and pins status in the footer", () => {
    const { container } = render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        queryLoading
        onChangeScenarioId={vi.fn()}
      />,
    );
    const panel = container.querySelector(".impact-query-panel");
    const scroll = container.querySelector(".impact-query-panel__scroll");
    const actions = container.querySelector(".impact-query-panel__actions");
    expect(panel).toContainElement(scroll);
    expect(panel).toContainElement(actions);
    expect(scroll).toContainElement(screen.getByRole("heading", { name: /Scenario Selection/i }));
    expect(actions).toContainElement(screen.getByText(/Running Scenario/i));
  });

  it("does not render suggested prompts for an unknown scenario", () => {
    render(
      <ImpactQueryPanel
        scenarios={["custom-001"]}
        scenarioId="custom-001"
        onChangeScenarioId={vi.fn()}
      />,
    );
    expect(screen.queryByRole("heading", { name: /Suggested prompts/i })).not.toBeInTheDocument();
  });
});
