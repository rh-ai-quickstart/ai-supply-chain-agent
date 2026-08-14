import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CreateScenarioModal } from "./CreateScenarioModal";

vi.mock("../services/scenarioCreateService", () => ({
  proposeScenario: vi.fn(),
  createScenario: vi.fn(),
}));

import { createScenario, proposeScenario } from "../services/scenarioCreateService";

describe("CreateScenarioModal", () => {
  beforeEach(() => {
    vi.mocked(proposeScenario).mockReset();
    vi.mocked(createScenario).mockReset();
  });

  it("proposes a draft then creates and calls onCreated", async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    vi.mocked(proposeScenario).mockResolvedValue({
      success: true,
      draft: {
        name: "France Closure",
        scenario_id: "france-closure",
        description: "Closed.",
        affect_bbox: "-5,42,8,51",
        place_summary: "France",
        rationale: "Covers FIR",
      },
    });
    vi.mocked(createScenario).mockResolvedValue({
      success: true,
      scenario_id: "france-closure",
    });

    render(<CreateScenarioModal onCreated={onCreated} onClose={vi.fn()} />);

    await user.type(
      screen.getByLabelText(/Disruption description/i),
      "Close French airspace",
    );
    await user.click(screen.getByRole("button", { name: /Propose scenario/i }));

    expect(await screen.findByDisplayValue("france-closure")).toBeInTheDocument();
    expect(screen.getByText(/Covers FIR/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^Create scenario$/i }));
    expect(onCreated).toHaveBeenCalledWith("france-closure");
  });

  it("disables propose when the prompt is empty", () => {
    render(<CreateScenarioModal onClose={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Propose scenario/i })).toBeDisabled();
  });

  it("shows an alert when propose fails and does not render a draft", async () => {
    const user = userEvent.setup();
    vi.mocked(proposeScenario).mockResolvedValue({
      success: false,
      error: "prompt is required",
    });

    render(<CreateScenarioModal onCreated={vi.fn()} onClose={vi.fn()} />);
    await user.type(screen.getByLabelText(/Disruption description/i), "something");
    await user.click(screen.getByRole("button", { name: /Propose scenario/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/prompt is required/i);
    expect(screen.queryByRole("heading", { name: /Review draft/i })).not.toBeInTheDocument();
  });

  it("keeps the draft and skips onCreated when create fails", async () => {
    const user = userEvent.setup();
    const onCreated = vi.fn();
    vi.mocked(proposeScenario).mockResolvedValue({
      success: true,
      draft: {
        name: "France Closure",
        scenario_id: "france-closure",
        description: "Closed.",
        affect_bbox: "-5,42,8,51",
      },
    });
    vi.mocked(createScenario).mockResolvedValue({
      success: false,
      error: "upstream unavailable",
    });

    render(<CreateScenarioModal onCreated={onCreated} onClose={vi.fn()} />);
    await user.type(screen.getByLabelText(/Disruption description/i), "Close French airspace");
    await user.click(screen.getByRole("button", { name: /Propose scenario/i }));
    expect(await screen.findByDisplayValue("france-closure")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^Create scenario$/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/upstream unavailable/i);
    expect(onCreated).not.toHaveBeenCalled();
    expect(screen.getByDisplayValue("france-closure")).toBeInTheDocument();
  });

  it("prefills the prompt when initialPrompt is provided", () => {
    render(
      <CreateScenarioModal
        onClose={vi.fn()}
        initialPrompt="Headline: Port strike disrupts shipping"
      />,
    );
    expect(screen.getByLabelText(/Disruption description/i)).toHaveValue(
      "Headline: Port strike disrupts shipping",
    );
  });

  it("closes on Escape and the dismiss button", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<CreateScenarioModal onClose={onClose} />);

    expect(screen.getByRole("dialog", { name: /Create scenario/i })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);

    await user.click(screen.getByLabelText("Close dialog"));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
