import { describe, expect, it } from "vitest";
import { humanizeScenarioId, labelForScenario } from "./presetScenarioIds";

describe("labelForScenario", () => {
  it("uses preset labels when known", () => {
    expect(labelForScenario("opensky-uk-closure-001")).toBe("UK Airspace Closure");
  });

  it("humanizes unknown scenario ids", () => {
    expect(labelForScenario("france-airspace-closure")).toBe("France Airspace Closure");
    expect(humanizeScenarioId("port_strike_marseille")).toBe("Port Strike Marseille");
  });
});
