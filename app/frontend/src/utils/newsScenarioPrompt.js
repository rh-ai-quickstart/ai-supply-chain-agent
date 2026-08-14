/**
 * Format a news headline (RSS fields from `/api/v1/news`) as a natural-language
 * prompt for the create-scenario propose step.
 */
export function formatNewsItemForScenarioPrompt(item) {
  if (!item?.title?.trim()) {
    return "";
  }

  const lines = [
    "Create a supply-chain disruption scenario based on this news story.",
    "",
  ];

  if (item.source?.trim()) {
    lines.push(`Source: ${item.source.trim()}`);
  }
  lines.push(`Headline: ${item.title.trim()}`);

  if (item.published_at?.trim()) {
    lines.push(`Published: ${item.published_at.trim()}`);
  }
  if (item.summary?.trim()) {
    lines.push("", "Summary:", item.summary.trim());
  }
  if (item.link?.trim()) {
    lines.push("", `Article: ${item.link.trim()}`);
  }

  return lines.join("\n");
}
