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
    expect(screen.getByRole("heading", { name: /Impact Query/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Live Flights" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "UK Airspace Closure" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByLabelText(/Question/i)).toHaveValue(DEFAULT_IMPACT_QUESTION);
    expect(screen.getByRole("button", { name: /Run impact query/i })).toBeEnabled();
  });

  it("calls onChangeMapMode when Live Flights is clicked", async () => {
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
    await userEvent.click(screen.getByRole("button", { name: "Live Flights" }));
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
    expect(screen.getByRole("button", { name: /Run impact query/i })).toBeDisabled();
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
    await userEvent.click(screen.getByRole("button", { name: /Run impact query/i }));
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
    expect(screen.getByText(/Running impact query/i)).toBeInTheDocument();
    expect(screen.getByText("Upstream failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run impact query/i })).toBeDisabled();
  });
});
