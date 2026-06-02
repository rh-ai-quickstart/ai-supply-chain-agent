import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  apiGet,
  apiPost,
  apiPostFormData,
  apiPostNdjsonStream,
  parseNdjsonBuffer,
} from './apiClient';
import { consoleFetch, consoleFetchJSON } from '@openshift-console/dynamic-plugin-sdk';

const jsonPost = (consoleFetchJSON as unknown as { post: ReturnType<typeof vi.fn> }).post;

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

  it('apiPostNdjsonStream reads NDJSON via consoleFetch', async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('{"event":"token","delta":"Hi"}\n'));
        controller.enqueue(encoder.encode('{"event":"done","answer":"Hi"}\n'));
        controller.close();
      },
    });
    vi.mocked(consoleFetch).mockResolvedValue({ ok: true, body } as Response);

    const events: { event: string }[] = [];
    await apiPostNdjsonStream('/api/v1/chat', { input: 'q' }, {
      onEvent: (evt) => events.push(evt),
    });

    expect(consoleFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/chat'),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Accept: 'application/x-ndjson' }),
      }),
    );
    expect(events).toEqual([
      { event: 'token', delta: 'Hi' },
      { event: 'done', answer: 'Hi' },
    ]);
  });

  it('parseNdjsonBuffer splits complete lines', () => {
    const { events, remainder } = parseNdjsonBuffer(
      '{"event":"start"}\n{"event":"token","delta":"Hi"}\n{"event":"tok',
    );
    expect(events).toHaveLength(2);
    expect(remainder).toBe('{"event":"tok');
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
