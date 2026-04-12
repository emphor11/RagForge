import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../config";
import { FileText, Upload, AlertTriangle, FolderOpen, Trash2 } from "lucide-react";

const Dashboard = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [recentDocs, setRecentDocs] = useState([]);
  const [docsLoading, setDocsLoading] = useState(true);
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

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete "${id}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/documents/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });

      if (res.ok) {
        setRecentDocs(recentDocs.filter((doc) => doc.id !== id));
      } else {
        alert("Failed to delete document");
      }
    } catch (err) {
      console.error("Delete failed", err);
      alert("Something went wrong while deleting");
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file");
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      const data = await res.json();
      onUploadSuccess(data.document_id);
      setRecentDocs((current) => [
        {
          id: data.document_id,
          filename: file.name,
          upload_date: Date.now() / 1000,
          status: data.status,
          stage: data.stage,
          job_id: data.job_id,
        },
        ...current.filter((doc) => doc.id !== data.document_id),
      ].slice(0, 10));
      navigate(`/documents/${encodeURIComponent(data.document_id)}`);
    } catch (err) {
      setError("Something went wrong while uploading");
      console.error(err);
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

  return (
    <div className="dashboard-page">
      {error && (
        <div className="error-banner">
          <AlertTriangle /> {error}
        </div>
      )}

      {/* Hero Upload Zone */}
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
                  <Upload /> Upload & Analyze
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
                      <td>
                        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                          {doc.status && doc.status !== "completed" && (
                            <span className="badge badge-neutral">
                              {(doc.stage || doc.status).replaceAll("_", " ")}
                            </span>
                          )}
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
                          <button
                            className="btn-icon btn-icon-danger"
                            title="Delete Document"
                            onClick={(e) => handleDelete(doc.id, e)}
                          >
                            <Trash2 size={16} />
                          </button>
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
