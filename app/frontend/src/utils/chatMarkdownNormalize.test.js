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

  it("strips leaked tool-call brackets from assistant text", () => {
    const raw =
      'However, I can try to fetch headlines.\n\n[fetch_news(limit=12)]\n\n[knowledge_base(query="supply chain disruptions", max_results="5")]';
    const out = normalizeChatMarkdown(raw);
    expect(out).toBe("However, I can try to fetch headlines.");
    expect(out).not.toContain("fetch_news");
    expect(out).not.toContain("knowledge_base");
  });
});
