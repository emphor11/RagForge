import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../config";
import { FileText, Upload, AlertTriangle } from "lucide-react";

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
                        {new Date(doc.upload_date * 1000).toLocaleDateString(
                          "en-US",
                          {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          }
                        )}
                      </td>
                      <td>
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
