import { describe, expect, it } from "vitest";
import { normalizeChatMarkdown } from "./chatMarkdownNormalize";

describe("normalizeChatMarkdown", () => {
  it("inserts paragraph breaks before numbered lists after colon patterns", () => {
    const raw = "Risks: 1. First item";
    expect(normalizeChatMarkdown(raw)).toContain(":\n\n1.");
  });

  it("trims outer whitespace", () => {
    expect(normalizeChatMarkdown("  hello  ")).toBe("hello");
  });
});
