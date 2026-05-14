import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  fetchDashboardState,
  fetchVectorStores,
  postAssistantMessage,
  postSimulation,
  postTriggerWorldEvent,
} from './backendClient';

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock('../../services/apiClient', () => ({
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
}));

describe('backendClient', () => {
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiPost.mockReset();
  });

  it('fetchDashboardState calls state endpoint', async () => {
    mocks.apiGet.mockResolvedValue({ kpis: {} });
    await fetchDashboardState();
    expect(mocks.apiGet).toHaveBeenCalledWith('/api/v1/state');
  });

  it('postTriggerWorldEvent sends mapView', async () => {
    mocks.apiPost.mockResolvedValue({});
    await postTriggerWorldEvent('airFreight');
    expect(mocks.apiPost).toHaveBeenCalledWith('/api/v1/trigger-event', { mapView: 'airFreight' });
  });

  it('postSimulation sends scenario and optimize', async () => {
    mocks.apiPost.mockResolvedValue({});
    await postSimulation('port_strike', true);
    expect(mocks.apiPost).toHaveBeenCalledWith('/api/v1/simulate', {
      scenario: 'port_strike',
      optimize: true,
    });
  });

  it('fetchVectorStores calls vector store endpoint', async () => {
    mocks.apiGet.mockResolvedValue({ vector_stores: [] });
    await fetchVectorStores();
    expect(mocks.apiGet).toHaveBeenCalledWith('/api/v1/vector_stores');
  });

  it('postAssistantMessage omits optional fields when absent', async () => {
    mocks.apiPost.mockResolvedValue({});
    await postAssistantMessage('hello', [], undefined);
    expect(mocks.apiPost).toHaveBeenCalledWith('/api/v1/chat', { input: 'hello' });
  });

  it('postAssistantMessage includes trimmed vector_store_id and history', async () => {
    mocks.apiPost.mockResolvedValue({});
    await postAssistantMessage('q', [{ role: 'human', content: 'prev' }], '  vs-1  ');
    expect(mocks.apiPost).toHaveBeenCalledWith('/api/v1/chat', {
      input: 'q',
      chat_history: [{ role: 'human', content: 'prev' }],
      vector_store_id: 'vs-1',
    });
  });
});
