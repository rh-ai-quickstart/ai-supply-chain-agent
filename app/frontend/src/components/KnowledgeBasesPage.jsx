import PropTypes from "prop-types";
import { useRef, useState } from "react";
import { useKnowledgeBases } from "../hooks/useKnowledgeBases";

export function KnowledgeBasesPage({ onKnowledgeBaseCreated }) {
  const fileInputRef = useRef(null);
  const [hasFiles, setHasFiles] = useState(false);
  const kb = useKnowledgeBases(onKnowledgeBaseCreated);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = kb.name.trim();
    const files = fileInputRef.current?.files ?? null;
    const created = await kb.submit(trimmed, files);
    if (created) {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setHasFiles(false);
    }
  };

  return (
    <div className="kb-page-root">
      <section className="kb-card panel">
        <h2 className="kb-card-title">Create knowledge base</h2>
        <p className="kb-help muted">
          Upload text or PDF files. The API creates a LlamaStack vector store, ingests your documents, and
          records a catalog entry (demo JSON under /tmp by default). Chat auto-selects a matching store
          for the active impact scenario by name keywords (UK/NATS, port strike, Suez).
        </p>
        {kb.submitError ? (
          <p className="kb-alert error" role="alert">
            {kb.submitError}
          </p>
        ) : null}
        {kb.warnings.length > 0 ? (
          <div className="kb-alert kb-warn" role="status">
            <strong>Some files were skipped or failed</strong>
            <ul>
              {kb.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <form className="kb-form" onSubmit={handleSubmit}>
          <label className="kb-label" htmlFor="kb-display-name">
            Display name <span className="kb-required">*</span>
          </label>
          <input
            id="kb-display-name"
            className="kb-input"
            type="text"
            value={kb.name}
            onChange={(e) => kb.setName(e.target.value)}
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
          <button className="kb-submit" type="submit" disabled={kb.saving || !kb.name.trim() || !hasFiles}>
            {kb.saving ? "Uploading…" : "Create and ingest"}
          </button>
        </form>
      </section>

      <section className="kb-card panel">
        <h2 className="kb-card-title">Registered knowledge bases</h2>
        {kb.loadError ? (
          <p className="error" role="alert">
            {kb.loadError}
          </p>
        ) : null}
        {kb.loading ? (
          <p className="muted">Loading knowledge bases…</p>
        ) : kb.rows.length === 0 ? (
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
                {kb.rows.map((row) => (
                  <tr key={row.id || row.vector_store_id || row.name}>
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

KnowledgeBasesPage.propTypes = {
  onKnowledgeBaseCreated: PropTypes.func,
};
