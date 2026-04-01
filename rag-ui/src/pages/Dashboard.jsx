import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";

const Dashboard = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

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
      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed");

      const data = await res.json();
      onUploadSuccess(data.document_id);
      // Navigate to the analysis page for the new document
      navigate(`/documents/${encodeURIComponent(data.document_id)}`);
    } catch (err) {
      setError("Something went wrong while uploading");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard-page">
      {error && <div className="error-banner">⚠️ {error}</div>}

      <div className="top-row">
        <div className="upload-card" style={{ width: '100%', maxWidth: '600px', margin: '0 auto' }}>
          <div className="upload-card-icon">☁️</div>
          <div className="upload-card-content">
            <div className="upload-card-title">Upload New Document</div>
            <div className="upload-card-desc">
              Get started by uploading a PDF, DOCX, or TXT file.
            </div>

            <input
              ref={fileInputRef}
              type="file"
              className="upload-file-input"
              id="file-input"
              onChange={(e) => setFile(e.target.files[0])}
            />
            <label htmlFor="file-input" className="upload-file-label">
              📎 {file ? file.name : "Choose File"}
            </label>

            <button
              className={`upload-card-btn ${loading ? "loading" : ""}`}
              onClick={handleUpload}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Analyzing...
                </>
              ) : (
                <>↑ Upload & Analyze</>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="empty-state" style={{ marginTop: '40px' }}>
        <div className="empty-state-icon">🚀</div>
        <div className="empty-state-title">Ready for Analysis?</div>
        <div className="empty-state-desc">
          Upload a file above to extract insights, risks, and recommendations using AI.
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
