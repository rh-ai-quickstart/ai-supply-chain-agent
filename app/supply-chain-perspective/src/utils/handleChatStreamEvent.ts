import type { ChatMessage, ChatStreamEvent } from '../types/dashboard';

function resolveAnswer(evt: ChatStreamEvent, fallback: string): string {
  return typeof evt.answer === 'string' && evt.answer.trim() ? evt.answer : fallback;
}

export type ChatStreamHandlerOptions = {
  updateStreamingMessage: (_updater: (_msg: ChatMessage) => ChatMessage) => void;
  setChatError: (_message: string) => void;
  emptyAnswerText: string;
  streamFailedText: string;
};

/** Apply one NDJSON chat event to the in-flight assistant message. */
export function handleChatStreamEvent(
  evt: ChatStreamEvent | null | undefined,
  options: ChatStreamHandlerOptions,
): void {
  if (!evt?.event) {
    return;
  }
  const { updateStreamingMessage, setChatError, emptyAnswerText, streamFailedText } = options;

  if (evt.event === 'token' && typeof evt.delta === 'string') {
    updateStreamingMessage((msg) => ({
      ...msg,
      content: msg.content + evt.delta,
    }));
    return;
  }
  if (evt.event === 'message') {
    updateStreamingMessage((msg) => ({
      ...msg,
      content: resolveAnswer(evt, emptyAnswerText),
      streaming: false,
      completion: evt.completion ?? null,
      routeData: evt.routeData,
    }));
    return;
  }
  if (evt.event === 'done') {
    updateStreamingMessage((msg) => ({
      ...msg,
      content: resolveAnswer(evt, emptyAnswerText),
      streaming: false,
      completion: evt.completion ?? null,
    }));
    return;
  }
  if (evt.event === 'error') {
    setChatError(evt.message || streamFailedText);
    updateStreamingMessage((msg) => ({
      ...msg,
      streaming: false,
    }));
  }
}
