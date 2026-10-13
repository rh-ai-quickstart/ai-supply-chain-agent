/** Tool-call text some models leak into the assistant reply, e.g. ``[fetch_news(limit=12)]``. */
const LEAKED_TOOL_CALL_RE = /\[\s*[A-Za-z_][\w]*\s*\([^()[\]]*\)\s*\]/g;

/** Normalizes assistant markdown so numbered lists break cleanly after colons / sentence ends. */
export function normalizeChatMarkdown(markdown) {
  let text = String(markdown ?? "").trim();
  // Drop pseudo tool-call brackets so the UI never shows orchestration noise.
  text = text.replace(LEAKED_TOOL_CALL_RE, "").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
  text = text.replace(/([:;])\s+(\d{1,2}\.\s+(?=\S))/g, "$1\n\n$2");
  text = text.replace(/([.!?])\s+(\d{1,2}\.\s+(?=\S))/g, "$1\n\n$2");
  return text;
}
