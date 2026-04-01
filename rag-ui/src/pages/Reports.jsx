import { useState, useEffect } from "react";

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
      const res = await fetch("http://127.0.0.1:8000/reports");
      if (!res.ok) throw new Error("Failed to load reports");
      const result = await res.json();
      setData(result);
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
        <span className="spinner" style={{ marginBottom: '20px' }}></span>
        <div className="empty-state-title">Aggregating Intelligence</div>
        <div className="empty-state-desc">Synthesizing findings across your entire document library...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠️</div>
        <div className="empty-state-title">Generation Failed</div>
        <div className="empty-state-desc">{error}</div>
        <button className="sidebar-upgrade-btn" onClick={fetchReports} style={{ marginTop: '20px' }}>Retry Aggregation</button>
      </div>
    );
  }

  return (
    <div className="reports-page">
      {/* 🔥 1. TOTAL NUMBERS (TOP) */}
      <div className="stats-row" style={{ marginBottom: '24px' }}>
        <div className="stat-card">
          <div className="stat-icon icon-bg-blue">📁</div>
          <div className="stat-value">{data.total_docs}</div>
          <div className="stat-label">Total Documents</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-red">🛡️</div>
          <div className="stat-value">{data.total_risks}</div>
          <div className="stat-label">Total Risks Found</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon icon-bg-purple">🚀</div>
          <div className="stat-value">{data.total_actions}</div>
          <div className="stat-label">Total Actions Required</div>
        </div>
      </div>

      <div className="two-col-grid">
        {/* 🔥 2. RISK SUMMARY */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-red">📊</div>
              Risk Breakdown
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="risk-item" style={{ fontSize: '15px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                   <span className="risk-dot high"></span>
                   <strong>High Severity</strong>
                </div>
                <span className="risk-badge high">{data.risk_summary.high}</span>
              </div>
              <div className="risk-item" style={{ fontSize: '15px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                   <span className="risk-dot medium"></span>
                   <strong>Medium Severity</strong>
                </div>
                <span className="risk-badge medium">{data.risk_summary.medium}</span>
              </div>
              <div className="risk-item" style={{ fontSize: '15px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                   <span className="risk-dot low"></span>
                   <strong>Low Severity</strong>
                </div>
                <span className="risk-badge low">{data.risk_summary.low}</span>
              </div>
            </div>
          </div>
        </div>

        {/* 🔥 3. TOP INSIGHTS */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-green">💡</div>
              Top Insights Feed
            </div>
          </div>
          <div className="card-body">
            <ul className="insight-list">
              {data.top_insights.length > 0 ? (
                data.top_insights.map((ins, idx) => (
                  <li key={idx} className="insight-item" style={{ paddingBottom: '12px', borderBottom: idx < data.top_insights.length - 1 ? '1px solid var(--gray-100)' : 'none' }}>
                    <span className="insight-bullet">👉</span>
                    {ins}
                  </li>
                ))
              ) : (
                <div className="empty-state-desc">No insights extracted yet.</div>
              )}
            </ul>
          </div>
        </div>
      </div>

      {/* 🔥 4. DOCUMENT LIST */}
      <div className="card full-width">
        <div className="card-header">
          <div className="card-title">
            <div className="card-title-icon icon-bg-blue">📋</div>
            Document Registry Summary
          </div>
        </div>
        <div className="card-body">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {data.doc_list.length > 0 ? (
              data.doc_list.map((doc, idx) => (
                <div key={idx} className="card" style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '20px', background: 'var(--gray-50)' }}>
                  <div style={{ fontSize: '24px' }}>📄</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '600', fontSize: '15px' }}>{doc.name}</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>{doc.summary}</div>
                  </div>
                  <div style={{ color: 'var(--primary-500)', fontWeight: '600', fontSize: '13px' }}>Analyzed ✓</div>
                </div>
              ))
            ) : (
              <div className="empty-state-desc">No documents found in the registry.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reports;
