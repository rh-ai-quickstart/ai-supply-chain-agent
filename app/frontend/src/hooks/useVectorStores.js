import { useCallback, useEffect, useState } from "react";
import { getVectorStores } from "../services/dashboardService";

/**
 * Loads the LlamaStack vector stores used for chat RAG retrieval, extracted
 * from `App.jsx` (SRP). `reloadVectorStores` is also handed to
 * `KnowledgeBasesPage` so a newly created knowledge base's vector store
 * shows up in chat without a full page reload.
 */
export function useVectorStores() {
  const [vectorStores, setVectorStores] = useState([]);
  const [vectorStoresError, setVectorStoresError] = useState("");

  const reloadVectorStores = useCallback(async (signal) => {
    try {
      const res = await getVectorStores({ signal });
      if (signal?.aborted) return;
      setVectorStores(Array.isArray(res.vector_stores) ? res.vector_stores : []);
      setVectorStoresError("");
    } catch (err) {
      if (err?.name === "AbortError") return;
      setVectorStores([]);
      setVectorStoresError("Unable to load knowledge bases for chat retrieval.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    reloadVectorStores(controller.signal);
    return () => controller.abort();
  }, [reloadVectorStores]);

  return { vectorStores, vectorStoresError, reloadVectorStores };
}
