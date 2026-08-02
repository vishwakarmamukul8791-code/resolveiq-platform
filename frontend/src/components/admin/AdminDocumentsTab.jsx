// frontend/src/components/admin/AdminDocumentsTab.jsx
//
// Upload is a two-step backend process: POST /upload saves the raw file
// (and may rename it if a file with that name already exists), then
// POST /process-document?filename=<the returned name> actually chunks,
// embeds, and indexes it. This chains both calls into one "Upload"
// action rather than exposing two separate buttons for what's really a
// single user intent.

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { documentsApi, ApiError } from "../../api/client";
import SourceViewerModal from "../SourceViewerModal";

const ALLOWED_EXTENSIONS = [".pdf", ".csv", ".txt"];
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

function AdminDocumentsTab() {
  const [documents, setDocuments] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);

  const [search, setSearch] = useState("");
  const [uploadStage, setUploadStage] = useState(null); // null | "uploading" | "processing"
  const [uploadNotice, setUploadNotice] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  const [deletingName, setDeletingName] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [previewingDoc, setPreviewingDoc] = useState(null);

  const fileInputRef = useRef(null);

  const loadDocuments = useCallback(() => {
    setStatus("loading");
    documentsApi
      .list()
      .then((data) => {
        setDocuments(data.documents ?? []);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : "Could not load documents.");
        setStatus("error");
      });
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return documents;
    return documents.filter((d) => d.document_name.toLowerCase().includes(q));
  }, [documents, search]);

  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file again later
    if (!file) return;

    const lower = file.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
      setUploadError("Unsupported file type — only .pdf, .csv, and .txt are accepted.");
      setUploadNotice(null);
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError("File is too large — maximum upload size is 10 MB.");
      setUploadNotice(null);
      return;
    }

    setUploadError(null);
    setUploadNotice(null);
    setUploadStage("uploading");

    try {
      const uploadResult = await documentsApi.upload(file);
      setUploadStage("processing");

      const processResult = await documentsApi.process(uploadResult.filename);

      if (processResult.message === "Document already exists") {
        setUploadNotice(
          `"${uploadResult.filename}" matches a document that's already indexed — nothing new to process.`
        );
      } else {
        setUploadNotice(
          `"${processResult.filename}" indexed — ${processResult.total_chunks} chunks created.`
        );
      }

      loadDocuments();
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploadStage(null);
    }
  }

  async function handleDelete(doc) {
    if (
      !window.confirm(
        `Delete "${doc.document_name}"? This removes it from the index permanently and can't be undone.`
      )
    ) {
      return;
    }

    setActionError(null);
    setDeletingName(doc.document_name);
    try {
      await documentsApi.remove(doc.document_name);
      setDocuments((prev) => prev.filter((d) => d.document_name !== doc.document_name));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not delete document.");
    } finally {
      setDeletingName(null);
    }
  }

  if (status === "loading") {
    return (
      <div className="admin-panel">
        <p className="admin-hint">Loading documents…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="admin-panel">
        <p className="admin-hint error">{error}</p>
      </div>
    );
  }

  return (
    <section className="admin-panel">
      <div className="panel-heading">
        <div>
          <span className="section-label">DOCUMENTS</span>
          <h2>Knowledge base</h2>
        </div>

        <div className="panel-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.csv,.txt"
            className="hidden-file-input"
            onChange={handleFileChange}
          />

          <button
            type="button"
            className="export-button secondary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadStage !== null}
          >
            {uploadStage === "uploading"
              ? "Uploading…"
              : uploadStage === "processing"
              ? "Processing…"
              : "+ Upload Document"}
          </button>
        </div>
      </div>

      {uploadError && <p className="admin-hint error">{uploadError}</p>}
      {uploadNotice && <p className="admin-hint success">{uploadNotice}</p>}
      {actionError && <p className="admin-hint error">{actionError}</p>}

      <div className="table-toolbar">
        <input
          type="text"
          placeholder="Search documents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span>
          Showing {filtered.length} of {documents.length} documents
        </span>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>DOCUMENT</th>
              <th>ACTIONS</th>
            </tr>
          </thead>

          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={2} className="empty-row">
                  {documents.length === 0
                    ? "No documents indexed yet — upload one to get started."
                    : "No matches."}
                </td>
              </tr>
            )}

            {filtered.map((doc) => {
              const isDeleting = deletingName === doc.document_name;

              return (
                <tr key={doc.document_name}>
                  <td>{doc.document_name}</td>

                  <td>
                    <div className="row-actions">
                      <button
                        type="button"
                        className="row-action"
                        onClick={() => setPreviewingDoc(doc)}
                      >
                        View
                      </button>

                      <button
                        type="button"
                        className="row-action danger"
                        onClick={() => handleDelete(doc)}
                        disabled={isDeleting}
                      >
                        {isDeleting ? "Deleting…" : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {previewingDoc && (
        <SourceViewerModal
          source={{ document_name: previewingDoc.document_name }}
          onClose={() => setPreviewingDoc(null)}
        />
      )}
    </section>
  );
}

export default AdminDocumentsTab;
