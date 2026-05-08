import type { VectorStoreSummary } from '../types/dashboard';
import type { KnowledgeBaseRecord } from '../types/knowledgeBases';
import { fetchVectorStores } from '../components/dashboard/backendClient';
import { apiGet, apiPostFormData } from './apiClient';

function vectorStoreCreatedAtToIso(createdAt?: number | string): string {
  if (createdAt == null || createdAt === '') {
    return new Date().toISOString();
  }
  if (typeof createdAt === 'string') {
    return createdAt;
  }
  const ms = createdAt < 1e12 ? createdAt * 1000 : createdAt;
  return new Date(ms).toISOString();
}

function mergeCatalogWithVectorStores(
  catalog: KnowledgeBaseRecord[],
  vectorStores: VectorStoreSummary[],
): KnowledgeBaseRecord[] {
  const byVsId = new Map<string, KnowledgeBaseRecord>();
  for (const row of catalog) {
    const vid = (row.vector_store_id || '').trim();
    if (vid) {
      byVsId.set(vid, row);
    }
  }

  const storeIds = new Set(
    vectorStores.map((s) => (s.id || '').trim()).filter((id) => id.length > 0),
  );

  const out: KnowledgeBaseRecord[] = [];

  for (const s of vectorStores) {
    const sid = (s.id || '').trim();
    if (!sid) {
      continue;
    }
    const cat = byVsId.get(sid);
    if (cat) {
      out.push(cat);
    } else {
      out.push({
        id: `vs:${sid}`,
        name: (s.name || sid).trim(),
        vector_store_id: sid,
        files: [],
        createdAt: vectorStoreCreatedAtToIso(s.created_at),
        source: 'llamastack',
      });
    }
  }

  for (const [vid, cat] of byVsId) {
    if (!storeIds.has(vid)) {
      out.push({ ...cat, source: 'catalog_only' });
    }
  }

  out.sort((a, b) =>
    (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }),
  );
  return out;
}

/** UI catalog rows only (POST /knowledge-bases appends here). */
export async function fetchKnowledgeBaseCatalog(): Promise<KnowledgeBaseRecord[]> {
  const data = await apiGet<{ knowledge_bases: KnowledgeBaseRecord[] }>('/api/v1/knowledge-bases');
  return data.knowledge_bases ?? [];
}

/** Table rows: ``fetchVectorStores`` (same as chat) merged with the catalog. */
export async function listKnowledgeBases(): Promise<KnowledgeBaseRecord[]> {
  const [storesRes, catalog] = await Promise.all([
    fetchVectorStores(),
    fetchKnowledgeBaseCatalog(),
  ]);
  return mergeCatalogWithVectorStores(catalog, storesRes.vector_stores ?? []);
}

export async function createKnowledgeBase(
  name: string,
  fileList: FileList | null,
): Promise<{ knowledge_base: KnowledgeBaseRecord; warnings?: string[] }> {
  const formData = new FormData();
  formData.append('name', name);
  if (fileList) {
    for (let i = 0; i < fileList.length; i += 1) {
      formData.append('files', fileList[i]);
    }
  }
  return apiPostFormData<{ knowledge_base: KnowledgeBaseRecord; warnings?: string[] }>(
    '/api/v1/knowledge-bases',
    formData,
  );
}
