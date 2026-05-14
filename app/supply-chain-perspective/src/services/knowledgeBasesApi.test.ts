import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createKnowledgeBase, listKnowledgeBases } from './knowledgeBasesApi';

const mocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPostFormData: vi.fn(),
  fetchVectorStores: vi.fn(),
}));

vi.mock('./apiClient', () => ({
  apiGet: mocks.apiGet,
  apiPostFormData: mocks.apiPostFormData,
}));

vi.mock('../components/dashboard/backendClient', () => ({
  fetchVectorStores: mocks.fetchVectorStores,
}));

describe('knowledgeBasesApi', () => {
  beforeEach(() => {
    mocks.apiGet.mockReset();
    mocks.apiPostFormData.mockReset();
    mocks.fetchVectorStores.mockReset();
  });

  it('listKnowledgeBases merges catalog with vector stores', async () => {
    mocks.fetchVectorStores.mockResolvedValue({
      vector_stores: [
        { id: 'vs-b', name: 'Beta Store' },
        { id: 'vs-a', name: 'Alpha Store' },
      ],
    });
    mocks.apiGet.mockResolvedValue({
      knowledge_bases: [
        {
          name: 'Alpha',
          vector_store_id: 'vs-a',
          files: [],
          createdAt: '2020-01-01T00:00:00.000Z',
        },
      ],
    });
    const rows = await listKnowledgeBases();
    expect(rows.map((r) => r.name)).toEqual(['Alpha', 'Beta Store']);
    const beta = rows.find((r) => r.vector_store_id === 'vs-b');
    expect(beta?.source).toBe('llamastack');
  });

  it('marks catalog-only rows when store disappears', async () => {
    mocks.fetchVectorStores.mockResolvedValue({ vector_stores: [] });
    mocks.apiGet.mockResolvedValue({
      knowledge_bases: [{ name: 'Orphan', vector_store_id: 'gone', files: [] }],
    });
    const rows = await listKnowledgeBases();
    expect(rows).toHaveLength(1);
    expect(rows[0].source).toBe('catalog_only');
  });

  it('createKnowledgeBase posts multipart form with name only when files are absent', async () => {
    mocks.apiPostFormData.mockResolvedValue({
      knowledge_base: {
        id: '1',
        name: 'My KB',
        files: [],
        vector_store_id: 'vs-1',
        createdAt: '2020-01-01T00:00:00.000Z',
      },
    });
    await createKnowledgeBase('My KB', null);
    expect(mocks.apiPostFormData).toHaveBeenCalledTimes(1);
    const [, formData] = mocks.apiPostFormData.mock.calls[0];
    expect((formData as FormData).get('name')).toBe('My KB');
    expect((formData as FormData).getAll('files')).toHaveLength(0);
  });
});
