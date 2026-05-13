export interface KnowledgeBaseFileMeta {
  filename: string;
  file_id: string;
  bytes: number;
}

export interface KnowledgeBaseRecord {
  id: string;
  name: string;
  vector_store_id: string;
  files: KnowledgeBaseFileMeta[];
  createdAt: string;
  source?: 'llamastack' | 'catalog_only';
}
