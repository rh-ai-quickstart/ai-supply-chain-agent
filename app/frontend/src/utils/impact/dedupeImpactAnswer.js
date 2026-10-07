/**
 * Markdown section headings that duplicate structured Impact Results panels.
 * Matched case-insensitively against ATX (#) headings and plain title lines.
 */
const DUPLICATE_ANSWER_SECTIONS = {
  diversions: [
    /^#{1,6}\s*recommended\s+diversions?\b.*$/i,
    /^#{1,6}\s*recommended\s+reroutes?\b.*$/i,
    /^recommended\s+diversions?\s*$/i,
    /^recommended\s+reroutes?\s*$/i,
  ],
  options: [
    /^#{1,6}\s*summary\s+of\s+action\s+items?\b.*$/i,
    /^#{1,6}\s*response\s+options?\b.*$/i,
    /^#{1,6}\s*action\s+items?\b.*$/i,
    /^summary\s+of\s+action\s+items?\s*$/i,
    /^response\s+options?\s*$/i,
    /^action\s+items?\s*$/i,
  ],
  cost: [
    /^#{1,6}\s*estimated\s+cost(?:\s+of\s+impact)?\b.*$/i,
    /^#{1,6}\s*value\s+at\s+risk\b.*$/i,
    /^estimated\s+cost(?:\s+of\s+impact)?\s*$/i,
    /^value\s+at\s+risk\s*$/i,
  ],
};

function isSectionHeading(line) {
  const trimmed = line.trim();
  if (!trimmed) return false;
  if (/^#{1,6}\s+\S/.test(trimmed)) return true;
  return /^[A-Z][A-Za-z0-9/()-]*(?:\s+[A-Za-z0-9/()-]+){0,6}$/.test(trimmed);
}

/**
 * Drop prose answer sections that the sidebar already renders as structured UI
 * (interactive diversions, response options, KPI value-at-risk).
 */
export function dedupeImpactAnswer(
  answer,
  { hasReroutes = false, hasOptions = false, hasValueAtRisk = false } = {},
) {
  if (!answer || typeof answer !== "string") return answer || "";

  const patterns = [];
  if (hasReroutes) patterns.push(...DUPLICATE_ANSWER_SECTIONS.diversions);
  if (hasOptions) patterns.push(...DUPLICATE_ANSWER_SECTIONS.options);
  if (hasValueAtRisk) patterns.push(...DUPLICATE_ANSWER_SECTIONS.cost);
  if (patterns.length === 0) return answer.trim();

  const kept = [];
  let skipping = false;

  for (const line of answer.split("\n")) {
    const trimmed = line.trim();
    const matchesDrop = patterns.some((re) => re.test(trimmed));

    if (skipping) {
      if (isSectionHeading(line) && !matchesDrop) {
        skipping = false;
        kept.push(line);
      }
      continue;
    }

    if (matchesDrop) {
      skipping = true;
      continue;
    }
    kept.push(line);
  }

  return kept
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
