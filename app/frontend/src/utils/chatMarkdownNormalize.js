/** Normalizes assistant markdown so numbered lists break cleanly after colons / sentence ends. */
export function normalizeChatMarkdown(markdown) {
  let text = markdown.trim();
  text = text.replace(/([:;])\s+(\d{1,2}\.\s+(?=\S))/g, "$1\n\n$2");
  text = text.replace(/([.!?])\s+(\d{1,2}\.\s+(?=\S))/g, "$1\n\n$2");
  return text;
}
