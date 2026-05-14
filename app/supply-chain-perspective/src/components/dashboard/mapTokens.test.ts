import { afterEach, describe, expect, it, vi } from 'vitest';
import { readSemanticToken } from './mapTokens';

describe('readSemanticToken', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns trimmed CSS variable when set', () => {
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: () => '  #abc123  ',
    } as CSSStyleDeclaration);
    expect(readSemanticToken('--pf-t--fake', '#000')).toBe('#abc123');
  });

  it('returns fallback when token is empty', () => {
    vi.spyOn(window, 'getComputedStyle').mockReturnValue({
      getPropertyValue: () => '',
    } as CSSStyleDeclaration);
    expect(readSemanticToken('--missing', '#fafafa')).toBe('#fafafa');
  });
});
