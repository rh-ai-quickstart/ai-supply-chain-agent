import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CreateScenarioPage } from "./CreateScenarioPage";

vi.mock("../services/scenarioCreateService", () => ({
  proposeScenario: vi.fn(),
  createScenario: vi.fn(),
}));

import { createScenario, proposeScenario } from "../services/scenarioCreateService";

describe("CreateScenarioPage", () => {
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

    render(<CreateScenarioPage onCreated={onCreated} />);

    await user.type(
      screen.getByLabelText(/Disruption description/i),
      "Close French airspace",
    );
    await user.click(screen.getByRole("button", { name: /Propose scenario/i }));

    expect(await screen.findByDisplayValue("france-closure")).toBeInTheDocument();
    expect(screen.getByText(/Covers FIR/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Create scenario/i }));
    expect(onCreated).toHaveBeenCalledWith("france-closure");
  });
});
