/** @typedef {{ role: string, content?: string, completion?: unknown }} ChatMessageLike */
/** @typedef {{ type: 'delta', content: string } | { type: 'done', answer?: string, completion?: unknown } | { type: 'error', message: string }} ChatStreamEvent */

/**
 * Apply one SSE chat event to the in-flight message list (expects trailing AI placeholder).
 * @param {ChatMessageLike[]} messages
 * @param {ChatStreamEvent} event
 * @param {{ emptyAnswerFallback?: string }} [options]
 * @returns {ChatMessageLike[] | null} Updated list, or null when unchanged.
 */
export function applyChatStreamEvent(messages, event, options = {}) {
  const { emptyAnswerFallback = "No response from assistant." } = options;
  const last = messages[messages.length - 1];
  if (last?.role !== "ai") {
    return null;
  }

  if (event.type === "delta" && event.content) {
    const updated = [...messages];
    updated[updated.length - 1] = {
      ...last,
      content: `${last.content ?? ""}${event.content}`,
    };
    return updated;
  }

  if (event.type === "done") {
    const updated = [...messages];
    const answer =
      typeof event.answer === "string" && event.answer.trim()
        ? event.answer
        : (last.content ?? "") || emptyAnswerFallback;
    updated[updated.length - 1] = {
      ...last,
      content: answer,
      completion: event.completion ?? null,
    };
    return updated;
  }

  return null;
}

/**
 * Parse SSE `data:` lines from a fetch response body and invoke `onEvent` per event.
 * @param {Response} response
 * @param {(event: ChatStreamEvent) => void} onEvent
 */
export async function consumeChatSseStream(response, onEvent) {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Streaming response has no body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  const dispatchBlock = (block) => {
    for (const line of block.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) {
        continue;
      }
      const payload = trimmed.slice(5).trim();
      if (!payload) {
        continue;
      }
      onEvent(JSON.parse(payload));
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const block of parts) {
      dispatchBlock(block);
    }
  }

  if (buffer.trim()) {
    dispatchBlock(buffer);
  }
}
