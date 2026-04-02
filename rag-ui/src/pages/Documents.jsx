import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE_URL } from "../config";

const Documents = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
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

  return (
    <div className="documents-page">
      <div className="card full-width">
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon icon-bg-indigo">📂</div>
            My Documents
          </div>
        </div>
        <div className="card-body">
          {error && <div className="error-banner">⚠️ {error}</div>}
          
          <div className="stats-row" style={{ 
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', 
            gap: '20px',
            marginTop: '10px'
          }}>
            {loading ? (
              <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
                <span className="spinner" style={{ borderColor: 'rgba(99, 102, 241, 0.3)', borderLeftColor: 'var(--primary-500)' }}></span>
                <p>Loading document library...</p>
              </div>
            ) : documents.length > 0 ? (
              documents.map((doc) => (
                <div key={doc.id} className="card" style={{ padding: '20px', textAlign: 'left' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                    <div className="card-title-icon icon-bg-blue">📄</div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: '600', fontSize: '15px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {doc.filename}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        {new Date(doc.upload_date * 1000).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <button
                    className="sidebar-upgrade-btn"
                    onClick={() => navigate(`/documents/${encodeURIComponent(doc.id)}`)}
                    style={{ width: '100%', padding: '8px' }}
                  >
                    View Analysis →
                  </button>
                </div>
              ))
            ) : (
              <div className="empty-state" style={{ gridColumn: '1 / -1' }}>
                <div className="empty-state-icon">📂</div>
                <div className="empty-state-title">No documents yet</div>
                <div className="empty-state-desc">Upload a document on the Dashboard to see it here.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Documents;
