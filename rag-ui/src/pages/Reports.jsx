import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config";
import { AlertTriangle } from "lucide-react";

const Reports = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/reports`);
      if (!res.ok) throw new Error("Failed to load reports");
      setData(await res.json());
    } catch (err) {
      console.error(err);
      setError("Failed to generate intelligence reports across all documents.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner spinner-lg" style={{ marginBottom: "16px" }} />
        <div className="empty-state-title">Aggregating Intelligence</div>
        <div className="empty-state-desc">Synthesizing findings across your entire document library…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon"><AlertTriangle /></div>
        <div className="empty-state-title">Generation Failed</div>
        <div className="empty-state-desc">{error}</div>
        <button className="btn btn-primary" onClick={fetchReports} style={{ marginTop: "16px" }}>
          Retry Aggregation
        </button>
      </div>
    );
  }

  const totalRisks = (data.risk_summary?.high || 0) + (data.risk_summary?.medium || 0) + (data.risk_summary?.low || 0);
  const maxRisk = Math.max(data.risk_summary?.high || 0, data.risk_summary?.medium || 0, data.risk_summary?.low || 0, 1);

  return (
    <div className="reports-page">
      {/* Stat Cards */}
      <div className="stats-row" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="stat-card">
          <div className="stat-label">Total Documents</div>
          <div className="stat-value">{data.total_docs}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total Risks Found</div>
          <div className="stat-value">{data.total_risks}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Actions Required</div>
          <div className="stat-value">{data.total_actions}</div>
        </div>
      </div>

      <div className="two-col-grid">
        {/* Risk Breakdown — CSS bar chart */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Risk Breakdown</div>
          </div>
          <div className="card-body">
            <div className="risk-bar-group">
              <div className="risk-bar-item">
                <span className="risk-bar-label">High</span>
                <div className="risk-bar-track">
                  <div
                    className="risk-bar-fill high"
                    style={{ width: `${((data.risk_summary?.high || 0) / maxRisk) * 100}%` }}
                  />
                </div>
                <span className="risk-bar-count">{data.risk_summary?.high || 0}</span>
              </div>
              <div className="risk-bar-item">
                <span className="risk-bar-label">Medium</span>
                <div className="risk-bar-track">
                  <div
                    className="risk-bar-fill medium"
                    style={{ width: `${((data.risk_summary?.medium || 0) / maxRisk) * 100}%` }}
                  />
                </div>
                <span className="risk-bar-count">{data.risk_summary?.medium || 0}</span>
              </div>
              <div className="risk-bar-item">
                <span className="risk-bar-label">Low</span>
                <div className="risk-bar-track">
                  <div
                    className="risk-bar-fill low"
                    style={{ width: `${((data.risk_summary?.low || 0) / maxRisk) * 100}%` }}
                  />
                </div>
                <span className="risk-bar-count">{data.risk_summary?.low || 0}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Top Insights Feed */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Top Insights</div>
          </div>
          <div className="card-body">
            {data.top_insights?.length > 0 ? (
              data.top_insights.map((ins, idx) => (
                <div key={idx} className="insight-feed-item">
                  <span className={`insight-severity-dot ${idx < 2 ? "high" : idx < 4 ? "medium" : "low"}`} />
                  <div>
                    <div className="insight-feed-text">{ins}</div>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state-desc">No insights extracted yet.</div>
            )}
          </div>
        </div>
      </div>

      {/* Document Registry */}
      <div className="card full-width">
        <div className="card-header">
          <div className="card-title">Document Registry</div>
        </div>
        <div className="card-body">
          {data.doc_list?.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Summary</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.doc_list.map((doc, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 500, color: "var(--text-primary)" }}>{doc.name}</td>
                    <td style={{ color: "var(--text-muted)", fontSize: "13px", maxWidth: "400px" }}>
                      {doc.summary}
                    </td>
                    <td>
                      <span className="badge badge-low">Analyzed</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty-state-desc">No documents found in the registry.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Reports;
