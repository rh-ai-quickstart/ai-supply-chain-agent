import { useCallback, useEffect, useState } from "react";
import { createKnowledgeBase, listKnowledgeBases } from "../services/knowledgeBasesService";
import { getLogger } from "../utils/logger.js";

const logger = getLogger(import.meta.url);

/**
 * Knowledge-base list/create CRUD state, extracted from `KnowledgeBasesPage.jsx`
 * (SRP). The page component stays responsible only for the form/table markup
 * and the uncontrolled file `<input>` ref.
 */
export function useKnowledgeBases(onKnowledgeBaseCreated) {
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [warnings, setWarnings] = useState([]);

  const refresh = useCallback(async () => {
    try {
      logger.debug("useKnowledgeBases: refreshing");
      setLoadError("");
      const list = await listKnowledgeBases();
      setRows(list);
      logger.debug("useKnowledgeBases: loaded %d bases", list?.length || 0);
    } catch {
      logger.error("useKnowledgeBases refresh error");
      setLoadError("Unable to load knowledge bases.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  /** Creates a knowledge base from `trimmedName`/`files`; returns true on success. */
  const submit = useCallback(
    async (trimmedName, files) => {
      if (!trimmedName || saving || !files?.length) {
        return false;
      }
      logger.info("useKnowledgeBases submit: name=%s files=%d", trimmedName, files.length);
      setSubmitError("");
      setWarnings([]);
      setSaving(true);
      try {
        const result = await createKnowledgeBase(trimmedName, files);
        setName("");
        if (result.warnings?.length) {
          setWarnings(result.warnings);
        }
        logger.info("useKnowledgeBases submit success: name=%s", trimmedName);
        await refresh();
        onKnowledgeBaseCreated?.();
        return true;
      } catch (err) {
        logger.error("useKnowledgeBases submit error: %s", err.message);
        setSubmitError(err instanceof Error ? err.message : "Unable to create knowledge base.");
        return false;
      } finally {
        setSaving(false);
      }
    },
    [saving, refresh, onKnowledgeBaseCreated],
  );

  return { rows, name, setName, loading, saving, loadError, submitError, warnings, submit };
}
