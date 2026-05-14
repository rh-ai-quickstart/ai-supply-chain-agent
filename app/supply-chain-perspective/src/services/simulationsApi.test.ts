import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createSimulation, listSimulations } from './simulationsApi';

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock('./apiClient', () => ({
  apiGet: mocks.apiGet,
  apiPost: mocks.apiPost,
}));

describe('simulationsApi', () => {
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiPost.mockReset();
  });

  it('listSimulations returns array from API', async () => {
    mocks.apiGet.mockResolvedValue({ simulations: [{ id: '1', name: 'a' }] });
    await expect(listSimulations()).resolves.toEqual([{ id: '1', name: 'a' }]);
    expect(mocks.apiGet).toHaveBeenCalledWith('/api/v1/simulations');
  });

  it('createSimulation returns simulation payload', async () => {
    mocks.apiPost.mockResolvedValue({ simulation: { id: '2', name: 'n' } });
    await expect(createSimulation({ name: 'n', description: 'd' })).resolves.toEqual({
      id: '2',
      name: 'n',
    });
  });

  it('createSimulation throws when response is invalid', async () => {
    mocks.apiPost.mockResolvedValue({});
    await expect(createSimulation({ name: 'n', description: 'd' })).rejects.toThrow(
      'Invalid response',
    );
  });
});
