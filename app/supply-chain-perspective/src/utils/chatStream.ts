import type { ChatCompletionPayload, ChatMessage } from '../types/dashboard';

export type ChatStreamEvent =
  | { type: 'delta'; content: string }
  | {
      type: 'done';
      answer?: string;
      completion?: ChatCompletionPayload | null;
      routeData?: unknown;
    }
  | { type: 'error'; message: string };

export function applyChatStreamEvent(
  messages: ChatMessage[],
  event: ChatStreamEvent,
  options: { emptyAnswerFallback?: string } = {},
): ChatMessage[] | null {
  const { emptyAnswerFallback = 'No response from assistant.' } = options;
  const last = messages[messages.length - 1];
  if (last?.role !== 'ai') {
    return null;
  }

  if (event.type === 'delta' && event.content) {
    const updated = [...messages];
    updated[updated.length - 1] = {
      ...last,
      content: `${last.content}${event.content}`,
    };
    return updated;
  }

  if (event.type === 'done') {
    const updated = [...messages];
    const answer =
      typeof event.answer === 'string' && event.answer.trim()
        ? event.answer
        : last.content || emptyAnswerFallback;
    updated[updated.length - 1] = {
      ...last,
      content: answer,
      completion: event.completion ?? null,
    };
    return updated;
  }

  return null;
}

export async function consumeChatSseStream(
  response: Response,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Streaming response has no body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  const dispatchBlock = (block: string) => {
    for (const line of block.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data:')) {
        continue;
      }
      const payload = trimmed.slice(5).trim();
      if (!payload) {
        continue;
      }
      onEvent(JSON.parse(payload) as ChatStreamEvent);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';
    for (const block of parts) {
      dispatchBlock(block);
    }
  }

  if (buffer.trim()) {
    dispatchBlock(buffer);
  }
}
