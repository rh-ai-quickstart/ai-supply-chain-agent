function resolveAnswer(evt, fallback) {
  return typeof evt.answer === "string" && evt.answer.trim() ? evt.answer : fallback;
}

/**
 * Apply one NDJSON chat event to the in-flight assistant message.
 * Matches backend events: `token`, `message`, `done`, `error`.
 */
export function handleChatStreamEvent(evt, { updateStreamingMessage, setChatError, emptyAnswerText, streamFailedText }) {
  if (!evt || typeof evt.event !== "string") {
    return;
  }
  if (evt.event === "token" && typeof evt.delta === "string") {
    updateStreamingMessage((msg) => ({
      ...msg,
      content: msg.content + evt.delta,
    }));
    return;
  }
  if (evt.event === "message") {
    updateStreamingMessage((msg) => ({
      ...msg,
      content: resolveAnswer(evt, emptyAnswerText),
      streaming: false,
      completion: evt.completion ?? null,
      routeData: evt.routeData,
    }));
    return;
  }
  if (evt.event === "done") {
    updateStreamingMessage((msg) => ({
      ...msg,
      content: resolveAnswer(evt, emptyAnswerText),
      streaming: false,
      completion: evt.completion ?? null,
    }));
    return;
  }
  if (evt.event === "error") {
    setChatError(evt.message || streamFailedText);
    updateStreamingMessage((msg) => ({
      ...msg,
      streaming: false,
    }));
  }
}
