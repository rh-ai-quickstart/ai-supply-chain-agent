import { beforeEach, describe, expect, it, vi } from "vitest";
import { createScenario, proposeScenario } from "./scenarioCreateService";

vi.mock("./apiClient", () => ({
  apiPost: vi.fn(),
}));

import { apiPost } from "./apiClient";

describe("scenarioCreateService", () => {
  beforeEach(() => {
    vi.mocked(apiPost).mockReset();
  });

  it("proposeScenario posts prompt", async () => {
    vi.mocked(apiPost).mockResolvedValue({ success: true, draft: { scenario_id: "x" } });
    await expect(proposeScenario("Close France")).resolves.toEqual({
      success: true,
      draft: { scenario_id: "x" },
    });
    expect(apiPost).toHaveBeenCalledWith("/api/v1/scenarios/propose", { prompt: "Close France" }, {
      signal: undefined,
    });
  });

  it("createScenario posts draft", async () => {
    const draft = { scenario_id: "france-closure", name: "France" };
    vi.mocked(apiPost).mockResolvedValue({ success: true, scenario_id: "france-closure" });
    await expect(createScenario(draft)).resolves.toEqual({
      success: true,
      scenario_id: "france-closure",
    });
    expect(apiPost).toHaveBeenCalledWith("/api/v1/scenarios", draft, { signal: undefined });
  });
});
