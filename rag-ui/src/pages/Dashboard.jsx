import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../config";
import { FileText, Upload, AlertTriangle, FolderOpen, Trash2 } from "lucide-react";

const STAGE_LABELS = {
  uploading_source: "Saving document…",
  parsing_document: "Reading contract…",
  building_context: "Building contract context…",
  analysing_contract: "Extracting clauses and risks…",
  saving_results: "Saving results…",
  completed: "Analysis complete",
  failed: "Analysis failed",
};

const Dashboard = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [recentDocs, setRecentDocs] = useState([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [streamState, setStreamState] = useState(null);
  // Map of docId → "confirming" | undefined for inline delete
  const [deletingId, setDeletingId] = useState(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setDocsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/documents`);
      const data = await res.json();
      setRecentDocs(data.slice(0, 10));
    } catch (err) {
      console.error("Failed to fetch recent documents", err);
    } finally {
      setDocsLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });

      if (res.ok) {
        setRecentDocs(recentDocs.filter((doc) => doc.id !== id));
      } else {
        setError("Failed to delete document.");
      }
    } catch (err) {
      console.error("Delete failed", err);
      setError("Something went wrong while deleting.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file");
      return;
    }

    setLoading(true);
    setError(null);
    setStreamState({
      stage: "uploading_source",
      progress: 0,
      detail: "Preparing document upload",
    });

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/documents/analyse`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Upload failed");
      }
      if (!res.body) {
        throw new Error("Streaming analysis is not available.");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let completedDocumentId = null;

      const applyEvent = (event) => {
        const documentId = event.document_id || file.name;
        setStreamState({
          stage: event.stage || "uploading_source",
          progress: event.progress ?? 0,
          detail: event.detail || "",
        });

        setRecentDocs((current) => [
          {
            id: documentId,
            filename: file.name,
            upload_date: Date.now() / 1000,
            status: event.status || "processing",
            stage: event.stage || "uploading_source",
            job_id: event.job_id || null,
            error: event.error || null,
          },
          ...current.filter((doc) => doc.id !== documentId),
        ].slice(0, 10));

        if (event.stage === "failed") {
          throw new Error(event.error || event.detail || "Document analysis failed.");
        }

        if (event.stage === "completed") {
          completedDocumentId = documentId;
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          const payload = block
            .split("\n")
            .filter((line) => line.startsWith("data: "))
            .map((line) => line.slice(6))
            .join("\n");

          if (!payload) {
            continue;
          }

          applyEvent(JSON.parse(payload));
        }

        if (done) {
          break;
        }
      }

      if (!completedDocumentId) {
        throw new Error("Analysis stream ended before the document completed.");
      }

      onUploadSuccess(completedDocumentId);
      setFile(null);
      setStreamState(null);
      fetchDocuments();
      navigate(`/documents/${encodeURIComponent(completedDocumentId)}`);
    } catch (err) {
      setError("Something went wrong while uploading");
      console.error(err);
      setStreamState(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => setDragging(false);

  const formatUploadDate = (rawDate) => {
    const timestamp = Number(rawDate);
    if (!Number.isFinite(timestamp) || timestamp <= 0) {
      return "Pending";
    }

    return new Date(timestamp * 1000).toLocaleDateString(
      "en-US",
      {
        month: "short",
        day: "numeric",
        year: "numeric",
      }
    );
  };

  const getStatusBadge = (doc) => {
    if (!doc.status || doc.status === "completed") {
      return <span className="badge badge-low">Completed</span>;
    }
    if (doc.status === "failed") {
      return <span className="badge badge-high">Failed</span>;
    }
    return (
      <span className="badge badge-neutral">
        {(doc.stage || doc.status).replaceAll("_", " ")}
      </span>
    );
  };

  return (
    <div className="dashboard-page">
      {error && (
        <div className="error-banner">
          <AlertTriangle /> {error}
        </div>
      )}

      {/* Page Hero */}
      <div className="page-hero">
        <h1 className="page-hero-title">Contract Intelligence</h1>
        <p className="page-hero-subtitle">
          Upload a legal agreement to extract clauses, surface risks, and generate a full AI-powered review.
        </p>
      </div>

      {/* Upload Zone */}
      <div className="upload-hero">
        <input
          ref={fileInputRef}
          type="file"
          id="file-input"
          style={{ display: "none" }}
          onChange={(e) => setFile(e.target.files[0])}
          accept=".pdf,.docx,.txt"
        />
        <div
          className={`upload-zone ${dragging ? "dragging" : ""}`}
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="upload-icon">
            <FileText />
          </div>
          <div className="upload-zone-title">
            {file ? file.name : "Upload a contract for review"}
          </div>
          <div className="upload-zone-desc">
            {file
              ? "Ready to analyze"
              : "Drag and drop or click to browse"}
          </div>
          <div className="upload-formats">PDF · DOCX · TXT</div>
        </div>

        {file && (
          <div className="upload-selected">
            <button
              className="btn btn-primary"
              onClick={(e) => {
                e.stopPropagation();
                handleUpload();
              }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" /> Analyzing…
                </>
              ) : (
                <>
                  <Upload /> Upload &amp; Analyze
                </>
              )}
            </button>
            <button
              className="btn btn-ghost"
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
            >
              Clear
            </button>
          </div>
        )}

        {streamState && (
          <div style={{ marginTop: "14px", textAlign: "center", color: "var(--text-muted)" }}>
            <div style={{ fontSize: "13px", marginBottom: "4px" }}>
              {STAGE_LABELS[streamState.stage] || streamState.stage?.replaceAll("_", " ")}
              {typeof streamState.progress === "number" ? ` · ${streamState.progress}%` : ""}
            </div>
            {streamState.detail && (
              <div style={{ fontSize: "12px" }}>{streamState.detail}</div>
            )}
          </div>
        )}
      </div>

      {/* Recent Contracts Table */}
      <div style={{ marginTop: "48px" }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Recent Contracts</div>
          </div>
          <div className="card-body">
            {docsLoading ? (
              <div className="empty-state">
                <span className="spinner spinner-lg" />
              </div>
            ) : recentDocs.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Contract Name</th>
                    <th>Uploaded</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recentDocs.map((doc) => (
                    <tr key={doc.id}>
                      <td>
                        <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                          {doc.filename}
                        </span>
                      </td>
                      <td style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                        {formatUploadDate(doc.upload_date)}
                      </td>
                      <td>{getStatusBadge(doc)}</td>
                      <td>
                        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                          <span
                            className="table-link"
                            onClick={() =>
                              navigate(
                                `/documents/${encodeURIComponent(doc.id)}`
                              )
                            }
                          >
                            Review →
                          </span>

                          {/* Inline delete confirmation */}
                          {deletingId === doc.id ? (
                            <div className="inline-delete-confirm">
                              <span>Delete?</span>
                              <button
                                className="inline-delete-btn"
                                onClick={() => handleDelete(doc.id)}
                              >
                                Yes
                              </button>
                              <button
                                className="inline-cancel-btn"
                                onClick={() => setDeletingId(null)}
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              className="btn-icon btn-icon-danger"
                              title="Delete Document"
                              onClick={() => setDeletingId(doc.id)}
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">
                  <FolderOpen />
                </div>
                <div className="empty-state-title">No contracts yet</div>
                <div className="empty-state-desc">
                  Upload your first document above to begin analysis.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
