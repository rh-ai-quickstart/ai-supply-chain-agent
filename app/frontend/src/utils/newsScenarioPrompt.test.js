import { describe, expect, it } from "vitest";
import { formatNewsItemForScenarioPrompt } from "./newsScenarioPrompt";

describe("formatNewsItemForScenarioPrompt", () => {
  it("formats headline, source, summary, and link", () => {
    const prompt = formatNewsItemForScenarioPrompt({
      title: "Port strike disrupts shipping",
      source: "BBC",
      published_at: "2026-08-05T12:00:00Z",
      summary: "Dock workers walk out at major ports.",
      link: "https://example.com/story",
    });

    expect(prompt).toContain("Create a supply-chain disruption scenario");
    expect(prompt).toContain("Source: BBC");
    expect(prompt).toContain("Headline: Port strike disrupts shipping");
    expect(prompt).toContain("Published: 2026-08-05T12:00:00Z");
    expect(prompt).toContain("Dock workers walk out at major ports.");
    expect(prompt).toContain("Article: https://example.com/story");
  });

  it("returns empty string when title is missing", () => {
    expect(formatNewsItemForScenarioPrompt({ source: "BBC" })).toBe("");
  });
});
