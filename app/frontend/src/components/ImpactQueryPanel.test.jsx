import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DEFAULT_IMPACT_QUESTION } from "../services/presetScenarioIds";
import { ImpactQueryPanel } from "./ImpactQueryPanel";

describe("ImpactQueryPanel", () => {
  it("renders scenario buttons, question, and run button", () => {
    render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        mapMode="live"
        onChangeMapMode={vi.fn()}
        question={DEFAULT_IMPACT_QUESTION}
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: /Scenario Selection/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All Flights" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByLabelText(/Question/i)).toHaveValue(DEFAULT_IMPACT_QUESTION);
    expect(screen.getByRole("button", { name: /Run Scenario/i })).toBeEnabled();
  });

  it("calls onChangeMapMode when All Flights is clicked", async () => {
    const onChangeMapMode = vi.fn();
    render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        mapMode="scenario"
        onChangeMapMode={onChangeMapMode}
        question="q"
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
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
        question="q"
        onChangeScenarioId={onChangeScenarioId}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "UK Airspace Closure" }));
    expect(onChangeScenarioId).toHaveBeenCalledWith("opensky-uk-closure-001");
  });

  it("disables run when question is empty", () => {
    render(
      <ImpactQueryPanel
        scenarios={["s1"]}
        scenarioId="s1"
        question="   "
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Run Scenario/i })).toBeDisabled();
  });

  it("calls onRunQuery when run is clicked", async () => {
    const onRunQuery = vi.fn();
    render(
      <ImpactQueryPanel
        scenarios={["s1"]}
        scenarioId="s1"
        question="What is affected?"
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={onRunQuery}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Run Scenario/i }));
    expect(onRunQuery).toHaveBeenCalledTimes(1);
  });

  it("shows loading and error states", () => {
    render(
      <ImpactQueryPanel
        scenarios={["s1"]}
        scenarioId="s1"
        question="q"
        queryLoading
        queryError="Upstream failed"
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
      />,
    );
    expect(screen.getByText(/Running Scenario/i)).toBeInTheDocument();
    expect(screen.getByText("Upstream failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run Scenario/i })).toBeDisabled();
  });

  it("renders suggested prompts for the selected scenario and runs one on click", async () => {
    const onRunSuggestedPrompt = vi.fn();
    render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        question="q"
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
        onRunSuggestedPrompt={onRunSuggestedPrompt}
      />,
    );
    expect(screen.getByText(/Suggested prompts/i)).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /Show affected aircraft/i }),
    );
    expect(onRunSuggestedPrompt).toHaveBeenCalledWith(
      "Show affected aircraft and recommend diversions.",
    );
  });

  it("keeps scenario controls in a scroll region and pins the run action", () => {
    const { container } = render(
      <ImpactQueryPanel
        scenarios={["opensky-uk-closure-001"]}
        scenarioId="opensky-uk-closure-001"
        question="q"
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
      />,
    );
    const panel = container.querySelector(".impact-query-panel");
    const scroll = container.querySelector(".impact-query-panel__scroll");
    const actions = container.querySelector(".impact-query-panel__actions");
    expect(panel).toContainElement(scroll);
    expect(panel).toContainElement(actions);
    expect(scroll).toContainElement(screen.getByRole("heading", { name: /Scenario Selection/i }));
    expect(actions).toContainElement(screen.getByRole("button", { name: /Run Scenario/i }));
  });

  it("does not render suggested prompts for an unknown scenario", () => {
    render(
      <ImpactQueryPanel
        scenarios={["custom-001"]}
        scenarioId="custom-001"
        question="q"
        onChangeScenarioId={vi.fn()}
        onChangeQuestion={vi.fn()}
        onRunQuery={vi.fn()}
      />,
    );
    expect(screen.queryByText(/Suggested prompts/i)).not.toBeInTheDocument();
  });
});
