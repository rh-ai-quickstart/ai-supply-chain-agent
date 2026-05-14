import { describe, expect, it } from "vitest";
import { formatCompletionSummary } from "./chatCompletionMeta";

describe("formatCompletionSummary", () => {
  it("returns empty string for non-objects", () => {
    expect(formatCompletionSummary(null)).toBe("");
    expect(formatCompletionSummary(undefined)).toBe("");
    expect(formatCompletionSummary("x")).toBe("");
  });

  it("joins usage, model, and finish_reason when present", () => {
    const summary = formatCompletionSummary({
      model: "llama-3",
      usage: { total_tokens: 10, prompt_tokens: 4, completion_tokens: 6 },
      choices: [{ finish_reason: "stop" }],
    });
    expect(summary).toContain("10 tokens (in 4 · out 6)");
    expect(summary).toContain("model llama-3");
    expect(summary).toContain("finish stop");
  });

  it("uses placeholders when token fields are missing", () => {
    const summary = formatCompletionSummary({
      model: "m",
      usage: { total_tokens: 1 },
      choices: [],
    });
    expect(summary).toContain("in — · out —");
  });
});
