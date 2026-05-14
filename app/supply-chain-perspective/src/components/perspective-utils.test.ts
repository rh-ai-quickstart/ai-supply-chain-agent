import { describe, expect, it } from 'vitest';
import { getImportRedirectURL, getPerspectiveLandingPageURL } from './perspective-utils';

describe('perspective-utils', () => {
  it('returns dashboard landing URL', () => {
    expect(getPerspectiveLandingPageURL({}, true)).toBe('/supply-chain/dashboard');
    expect(getPerspectiveLandingPageURL({}, false)).toBe('/supply-chain/dashboard');
  });

  it('returns import redirect URL', () => {
    expect(getImportRedirectURL('demo-ns')).toBe('/supply-chain/dashboard');
  });
});
