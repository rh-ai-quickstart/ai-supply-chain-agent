import { useCallback, useEffect, useRef, useState } from "react";
import { createKnowledgeBase, listKnowledgeBases } from "../services/knowledgeBasesService";

export function KnowledgeBasesPage({ onKnowledgeBaseCreated }) {
  const fileInputRef = useRef(null);
  const [rows, setRows] = useState([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [warnings, setWarnings] = useState([]);
  const [hasFiles, setHasFiles] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setLoadError("");
      const list = await listKnowledgeBases();
      setRows(list);
    } catch {
      setLoadError("Unable to load knowledge bases.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = name.trim();
    const files = fileInputRef.current?.files ?? null;
    if (!trimmed || saving || !files?.length) {
      return;
    }
    setSubmitError("");
    setWarnings([]);
    setSaving(true);
    try {
      const result = await createKnowledgeBase(trimmed, files);
      setName("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setHasFiles(false);
      if (result.warnings?.length) {
        setWarnings(result.warnings);
      }
      await refresh();
      onKnowledgeBaseCreated?.();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Unable to create knowledge base.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="kb-page-root">
      <section className="kb-card panel">
        <h2 className="kb-card-title">Create knowledge base</h2>
        <p className="kb-help muted">
          Upload text or PDF files. The API creates a LlamaStack vector store, ingests your documents, and
          records a catalog entry (demo JSON under /tmp by default). Use the new vector store ID in chat.
        </p>
        {submitError ? (
          <p className="kb-alert error" role="alert">
            {submitError}
          </p>
        ) : null}
        {warnings.length > 0 ? (
          <div className="kb-alert kb-warn" role="status">
            <strong>Some files were skipped or failed</strong>
            <ul>
              {warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <form className="kb-form" onSubmit={(e) => void handleSubmit(e)}>
          <label className="kb-label" htmlFor="kb-display-name">
            Display name <span className="kb-required">*</span>
          </label>
          <input
            id="kb-display-name"
            className="kb-input"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="off"
          />
          <label className="kb-label" htmlFor="kb-documents">
            Documents <span className="kb-required">*</span>
          </label>
          <input
            id="kb-documents"
            ref={fileInputRef}
            className="kb-file-input"
            type="file"
            multiple
            accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf"
            onChange={() => setHasFiles(!!fileInputRef.current?.files?.length)}
          />
          <button className="kb-submit" type="submit" disabled={saving || !name.trim() || !hasFiles}>
            {saving ? "Uploading…" : "Create and ingest"}
          </button>
        </form>
      </section>

      <section className="kb-card panel">
        <h2 className="kb-card-title">Registered knowledge bases</h2>
        {loadError ? (
          <p className="error" role="alert">
            {loadError}
          </p>
        ) : null}
        {loading ? (
          <p className="muted">Loading knowledge bases…</p>
        ) : rows.length === 0 ? (
          <p className="muted">No knowledge bases yet.</p>
        ) : (
          <div className="kb-table-wrap">
            <table className="kb-table">
              <thead>
                <tr>
                  <th>Display name</th>
                  <th>Vector store ID</th>
                  <th>Files</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.name}</td>
                    <td>
                      <code className="kb-code">{row.vector_store_id}</code>
                    </td>
                    <td>
                      {row.files?.length ? row.files.map((f) => f.filename).join(", ") : "No files"}
                    </td>
                    <td>
                      {new Date(row.createdAt).toLocaleString(undefined, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
