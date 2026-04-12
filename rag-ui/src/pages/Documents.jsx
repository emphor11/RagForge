import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../config";
import { FolderOpen, AlertTriangle, Trash2 } from "lucide-react";

const Documents = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const navigate = useNavigate();

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/documents`);
      const data = await res.json();
      setDocuments(data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
      setError("Failed to load document library");
    } finally {
      setLoading(false);
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
        setDocuments(documents.filter((doc) => doc.id !== id));
      } else {
        alert("Failed to delete document");
      }
    } catch (err) {
      console.error("Delete failed", err);
      alert("Something went wrong while deleting");
    }
  };

  const guessDocType = (name) => {
    const n = (name || "").toLowerCase();
    if (n.includes("nda") || n.includes("non-disclosure")) return "NDA";
    if (n.includes("msa") || n.includes("master service")) return "MSA";
    if (n.includes("sow") || n.includes("statement of work")) return "SOW";
    if (n.includes("employ")) return "Employment";
    return "Contract";
  };

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
    <div className="documents-page">
      <div className="card">
        <div className="card-header">
          <div className="card-title">Documents</div>
          <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            {documents.length} total
          </span>
        </div>
        <div className="card-body">
          {error && (
            <div className="error-banner">
              <AlertTriangle /> {error}
            </div>
          )}

          {/* Filter bar */}
          <div className="filter-bar">
            {["all", "recent"].map((f) => (
              <button
                key={f}
                className={`filter-btn ${filter === f ? "active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : "Recent"}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="empty-state">
              <span className="spinner spinner-lg" />
            </div>
          ) : documents.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Contract Name</th>
                  <th>Type</th>
                  <th>Uploaded</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {documents
                  .filter((doc) => {
                    if (filter === "recent") {
                      const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
                      return Number(doc.upload_date) * 1000 > weekAgo;
                    }
                    return true;
                  })
                  .map((doc) => (
                    <tr key={doc.id}>
                      <td>
                        <span
                          style={{
                            fontWeight: 500,
                            color: "var(--text-primary)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            display: "block",
                            maxWidth: "400px",
                          }}
                        >
                          {doc.filename}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-neutral">
                          {guessDocType(doc.filename)}
                        </span>
                      </td>
                      <td
                        style={{
                          color: "var(--text-muted)",
                          fontSize: "13px",
                        }}
                      >
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
              <div className="empty-state-title">No documents yet</div>
              <div className="empty-state-desc">
                Upload a document on the Dashboard to see it here.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Documents;
