import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiGet, apiPost, apiPostFormData } from './apiClient';
import { consoleFetch, consoleFetchJSON } from '@openshift-console/dynamic-plugin-sdk';

const jsonPost = (consoleFetchJSON as { post: ReturnType<typeof vi.fn> }).post;

describe('apiClient (console proxy)', () => {
  beforeEach(() => {
    vi.mocked(consoleFetchJSON).mockReset();
    jsonPost.mockReset();
    vi.mocked(consoleFetch).mockReset();
  });

  it('apiGet delegates to consoleFetchJSON with resolved plugin URL', async () => {
    vi.mocked(consoleFetchJSON).mockResolvedValue({ ok: true });
    await expect(apiGet('/api/v1/state')).resolves.toEqual({ ok: true });
    expect(consoleFetchJSON).toHaveBeenCalledWith(
      expect.stringContaining('/api/plugins/supply-chain-perspective/api/v1/state'),
    );
  });

  it('apiPost delegates to consoleFetchJSON.post', async () => {
    jsonPost.mockResolvedValue({ id: 1 });
    await expect(apiPost('/api/v1/chat', { input: 'hi' })).resolves.toEqual({ id: 1 });
    expect(jsonPost).toHaveBeenCalledWith(
      expect.stringContaining('/api/plugins/supply-chain-perspective/api/v1/chat'),
      { input: 'hi' },
    );
  });

  it('apiPostFormData uses consoleFetch and parses JSON body', async () => {
    vi.mocked(consoleFetch).mockResolvedValue({
      ok: true,
      json: async () => ({ created: true }),
      text: async () => '',
    } as Response);
    const fd = new FormData();
    fd.append('name', 'kb');
    await expect(apiPostFormData('/api/v1/knowledge-bases', fd)).resolves.toEqual({
      created: true,
    });
    expect(consoleFetch).toHaveBeenCalled();
  });
});
