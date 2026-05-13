import type { ChatCompletionPayload } from '../../types/dashboard';

/** One-line summary for token counts and model from a serialized completion. */
export function formatCompletionSummary(completion: ChatCompletionPayload | null | undefined): string {
  if (!completion || typeof completion !== 'object') {
    return '';
  }
  const usage = completion.usage as Record<string, unknown> | undefined;
  const model = typeof completion.model === 'string' ? completion.model : undefined;
  const finish =
    Array.isArray(completion.choices) && completion.choices[0]
      ? (completion.choices[0] as Record<string, unknown>).finish_reason
      : undefined;

  const parts: string[] = [];
  if (usage && typeof usage === 'object') {
    const total = usage.total_tokens;
    const prompt = usage.prompt_tokens;
    const comp = usage.completion_tokens;
    if (typeof total === 'number') {
      const inTok = typeof prompt === 'number' ? prompt : '—';
      const outTok = typeof comp === 'number' ? comp : '—';
      parts.push(`${total} tokens (in ${inTok} · out ${outTok})`);
    }
  }
  if (model) {
    parts.push(`model ${model}`);
  }
  if (typeof finish === 'string' && finish) {
    parts.push(`finish ${finish}`);
  }
  return parts.join(' · ');
}
