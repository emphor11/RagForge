import { useState, useEffect } from "react";
import { API_BASE_URL } from "../config";

const Analytics = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/analytics`);
      if (!res.ok) throw new Error("Failed to load analytics");
      const result = await res.json();
      setData(result);
    } catch (err) {
      console.error(err);
      setError("Failed to retrieve system performance analytics.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" style={{ marginBottom: '20px' }}></span>
        <div className="empty-state-title">Calculating Metrics</div>
        <div className="empty-state-desc">Aggregating system performance and trend data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⚠️</div>
        <div className="empty-state-title">Analytics Unavailable</div>
        <div className="empty-state-desc">{error}</div>
        <button className="sidebar-upgrade-btn" onClick={fetchAnalytics} style={{ marginTop: '20px' }}>Retry Analysis</button>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      <div className="two-col-grid">
        {/* 🔥 1. DOCUMENT ACTIVITY */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-blue">📅</div>
              Document Activity
            </div>
          </div>
          <div className="card-body">
            <p className="summary-text" style={{ marginBottom: '12px' }}>Uploads over time:</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {Object.entries(data.docs_over_time).length > 0 ? (
                Object.entries(data.docs_over_time)
                  .sort((a, b) => b[0].localeCompare(a[0]))
                  .map(([date, count]) => (
                    <div key={date} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--gray-50)', borderRadius: '6px' }}>
                      <span style={{ fontSize: '13px', fontWeight: '500' }}>{date}</span>
                      <span style={{ fontSize: '13px', color: 'var(--primary-600)', fontWeight: '600' }}>{count} docs</span>
                    </div>
                  ))
              ) : (
                <div className="empty-state-desc">No activity recorded.</div>
              )}
            </div>
          </div>
        </div>

        {/* 🔥 2. RISK TREND */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-red">📉</div>
              Risk Trend
            </div>
          </div>
          <div className="card-body">
            <div style={{ textAlign: 'center', padding: '10px 0' }}>
               <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>System Status</div>
               <div style={{ fontSize: '24px', fontWeight: '700', marginTop: '8px', color: data.risk_trend.direction === 'down' ? 'var(--success)' : (data.risk_trend.direction === 'up' ? 'var(--danger)' : 'var(--text-primary)') }}>
                  Risks are {data.risk_trend.direction === 'down' ? 'decreasing ↓' : (data.risk_trend.direction === 'up' ? 'increasing ↑' : 'stable')}
               </div>
            </div>
            <div className="summary-meta" style={{ marginTop: '20px' }}>
               <div className="summary-meta-item">
                  <strong>Last Week:</strong> {data.risk_trend.last_week}
               </div>
               <div className="summary-meta-item">
                  <strong>This Week:</strong> {data.risk_trend.this_week}
               </div>
            </div>
          </div>
        </div>
      </div>

      <div className="two-col-grid">
        {/* 🔥 3. PERFORMANCE */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-green">⚡</div>
              Performance Metrics
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
               <div className="stat-card" style={{ boxShadow: 'none', background: 'var(--gray-50)' }}>
                  <div className="stat-value" style={{ fontSize: '20px' }}>{(data.performance.avg_confidence * 100).toFixed(0)}%</div>
                  <div className="stat-label">Avg Confidence</div>
               </div>
               <div className="stat-card" style={{ boxShadow: 'none', background: 'var(--gray-50)' }}>
                  <div className="stat-value" style={{ fontSize: '20px' }}>{data.performance.avg_response_time}s</div>
                  <div className="stat-label">Response Time</div>
               </div>
            </div>
          </div>
        </div>

        {/* 🔥 5. USAGE */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-title-icon icon-bg-purple">📊</div>
              Usage Stats
            </div>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
               <div className="stat-card" style={{ boxShadow: 'none', background: 'var(--gray-50)' }}>
                  <div className="stat-value" style={{ fontSize: '20px' }}>{data.usage.total_queries}</div>
                  <div className="stat-label">Queries Asked</div>
               </div>
               <div className="stat-card" style={{ boxShadow: 'none', background: 'var(--gray-50)' }}>
                  <div className="stat-value" style={{ fontSize: '20px' }}>{data.usage.total_analyses}</div>
                  <div className="stat-label">Analyses Done</div>
               </div>
            </div>
          </div>
        </div>
      </div>

      {/* Common Risks List (Simple Placeholder for now) */}
      <div className="card full-width">
        <div className="card-header">
           <div className="card-title">
              <div className="card-title-icon icon-bg-orange">⚠️</div>
              Common System Risks
           </div>
        </div>
        <div className="card-body">
           <ul className="risk-list">
              <li className="risk-item">
                 <div className="risk-item-left">
                    <span className="risk-dot high"></span>
                    Identity & Access Misconfiguration
                 </div>
                 <span className="risk-badge high">High Probability</span>
              </li>
              <li className="risk-item">
                 <div className="risk-item-left">
                    <span className="risk-dot medium"></span>
                    API Response Latency Spikes
                 </div>
                 <span className="risk-badge medium">Medium Probability</span>
              </li>
              <li className="risk-item">
                 <div className="risk-item-left">
                    <span className="risk-dot low"></span>
                    Context Window Overflows
                 </div>
                 <span className="risk-badge low">Low Probability</span>
              </li>
           </ul>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
