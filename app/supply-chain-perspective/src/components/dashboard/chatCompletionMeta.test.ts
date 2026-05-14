import { describe, expect, it } from 'vitest';
import { formatCompletionSummary } from './chatCompletionMeta';

describe('formatCompletionSummary', () => {
  it('returns empty for non-objects', () => {
    expect(formatCompletionSummary(null)).toBe('');
    expect(formatCompletionSummary(undefined)).toBe('');
  });

  it('joins usage model and finish', () => {
    const s = formatCompletionSummary({
      model: 'llama-3',
      usage: { total_tokens: 10, prompt_tokens: 4, completion_tokens: 6 },
      choices: [{ finish_reason: 'stop' }],
    });
    expect(s).toContain('10 tokens (in 4 · out 6)');
    expect(s).toContain('model llama-3');
    expect(s).toContain('finish stop');
  });
});
