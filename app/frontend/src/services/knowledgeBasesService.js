import { apiGet, apiPostFormData } from "./apiClient";
import { getVectorStores } from "./dashboardService";

function vectorStoreCreatedAtToIso(createdAt) {
  if (createdAt == null || createdAt === "") {
    return new Date().toISOString();
  }
  if (typeof createdAt === "string") {
    return createdAt;
  }
  const ms = createdAt < 1e12 ? createdAt * 1000 : createdAt;
  return new Date(ms).toISOString();
}

function mergeCatalogWithVectorStores(catalog, vectorStores) {
  const byVsId = new Map();
  for (const row of catalog) {
    const vid = (row.vector_store_id || "").trim();
    if (vid) {
      byVsId.set(vid, row);
    }
  }

  const storeIds = new Set(
    vectorStores.map((s) => (s.id || "").trim()).filter((id) => id.length > 0),
  );

  const out = [];

  for (const s of vectorStores) {
    const sid = (s.id || "").trim();
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
        source: "llamastack",
      });
    }
  }

  for (const [vid, cat] of byVsId) {
    if (!storeIds.has(vid)) {
      out.push({ ...cat, source: "catalog_only" });
    }
  }

  out.sort((a, b) => (a.name || "").localeCompare(b.name || "", undefined, { sensitivity: "base" }));
  return out;
}

async function fetchKnowledgeBaseCatalog() {
  const data = await apiGet("/api/v1/knowledge-bases");
  return Array.isArray(data.knowledge_bases) ? data.knowledge_bases : [];
}

/** Same vector stores as chat, merged with UI catalog for the Knowledge Bases table. */
export async function listKnowledgeBases() {
  const [storesRes, catalog] = await Promise.all([getVectorStores(), fetchKnowledgeBaseCatalog()]);
  const stores = Array.isArray(storesRes.vector_stores) ? storesRes.vector_stores : [];
  return mergeCatalogWithVectorStores(catalog, stores);
}

export async function createKnowledgeBase(name, fileList) {
  const formData = new FormData();
  formData.append("name", name);
  if (fileList?.length) {
    for (let i = 0; i < fileList.length; i += 1) {
      formData.append("files", fileList[i]);
    }
  }
  return apiPostFormData("/api/v1/knowledge-bases", formData);
}
